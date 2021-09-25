# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
import zlib

from httoop import METHOD_NOT_ALLOWED, URI
from saml2 import BINDING_HTTP_ARTIFACT, BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.client import Saml2Client
from saml2.metadata import create_metadata_string
from saml2.response import StatusError, UnsolicitedResponse, VerificationError
from saml2.s_utils import UnknownPrincipal, UnsupportedBinding, rndstr
from saml2.sigver import MissingKey, SignatureError

from circuits import Component, handler
from circuits.http.server.saml.models import (
	EmptyAuthnResponse, MultipleIdentityProvider, NoIdentityProvider, SamlAuthnResponse, SamlError,
	SamlHTTPResponse, SamlLogoutRequest, SamlLogoutResponse,
)


class ServiceProvider(Component):
	"""A SAML 2.0 Service Provider

	using pysaml2 from https://github.com/rohe/pysaml2/
	"""

	def init(self, configfile, *args, **kwargs):
		self.configfile = configfile
		self.sp = None

		self.bindings = [BINDING_HTTP_REDIRECT, BINDING_HTTP_POST, BINDING_HTTP_ARTIFACT]

		self.outstanding_queries = {}
		self.relay_states = {}
		self.reload()

	def reload(self):
		"""reload the SAML service provider configuration"""
		sys.modules.pop(os.path.splitext(os.path.basename(self.configfile))[0], None)
		self.sp = Saml2Client(config_file=self.configfile)

	def get_metadata(self, valid='4', cert=None, keyfile=None, mid=None, name=None, sign=None):
		"""get the XML metadata of this service provider"""
		return create_metadata_string(self.configfile, None, valid='4', cert=None, keyfile=None, mid=None, name=None, sign=False)

	@handler('single_sign_on')
	def do_single_sign_on(self, authn_request):
		"""Creates the SAML <AuthnRequest> request for single sign on for single sign on.
			Returns the appropriate HTTP response.
		"""
		identity_provider_entity_id = self.select_identity_provider(authn_request.preferred_identity_provider)
		binding, destination = self.get_identity_provider_destination(identity_provider_entity_id)

		kwargs = authn_request.kwargs
		state = authn_request.state
		relay_state = authn_request.relay_state
		kwargs['is_passive'] = 'true' if authn_request.is_passive else None

		if authn_request.service_provider_url:
			kwargs['assertion_consumer_service_urls'] = (authn_request.service_provider_url,)
		sid, message = self.sp.create_authn_request(destination, binding=authn_request.reply_binding, **kwargs)

		if state or relay_state:
			relay_state = relay_state or rndstr()
			self.relay_states[relay_state] = state

		http_args = self.sp.apply_binding(binding, message, destination, relay_state=relay_state)
		self.outstanding_queries[sid] = authn_request.service_provider_url
		return SamlHTTPResponse(http_args, binding)

	def parse_authn_respone(self, client):
		"""Parse a received SAML request"""
		binding, message, relay_state = self._get_saml_message(client)
		if not message:
			return
		try:
			response = self.sp.parse_authn_request_response(message, binding, self.outstanding_queries)
		except (UnknownPrincipal, UnsupportedBinding, VerificationError, UnsolicitedResponse, StatusError, MissingKey, SignatureError) as exc:
			raise SamlError.from_exception(exc)

		if response is None:
			raise EmptyAuthnResponse()
		return SamlAuthnResponse(response, binding, message, relay_state)

	def select_identity_provider(self, preferred_identity_provider=None):
		"""Select an identity provider based on the available identity providers.
			If multiple IDP's are set up the client might have specified one in the query string.
			Otherwise an error is raised where the user can choose one.

			Returns the EntityID of the IDP.
		"""
		idps = self.sp.metadata.with_descriptor("idpsso")
		if not idps and self.reload():
			idps = self.sp.metadata.with_descriptor("idpsso")
		if preferred_identity_provider and preferred_identity_provider in idps:
			return preferred_identity_provider
		if len(idps) == 1:
			return idps.keys()[0]
		if not idps:
			raise NoIdentityProvider()
		raise MultipleIdentityProvider(idps.keys())

	def get_identity_provider_destination(self, entity_id):
		"""Get the destination (with SAML binding) of the specified entity_id.

			Returns (binding, destination-URI)
		"""
		return self.sp.pick_binding("single_sign_on_service", self.bindings, "idpsso", entity_id=entity_id)

	def select_service_provider(self, client):
		"""Select the URI of the requested assertion consumer service and the reply binding which should be used.
			If tries to preserve the current request scheme (HTTP / HTTPS) and picks the same netloc (host or IP).
			If nothing is found for this it falls back to the regular full qualified host name of the service provider.

			Returns (binding, service-provider-URI)
		"""
		acs = self.sp.config.getattr("endpoints", "sp")["assertion_consumer_service"]
		service_url, reply_binding = acs[0]
		netloc = False
		p2 = client.request.uri
		for _url, _binding in acs:
			p1 = URI(_url)
			if p1.scheme == p2.scheme and p1.netloc == p2.netloc:
				netloc = True
				service_url, reply_binding = _url, _binding
				if p1.path == p2.path:
					break
			elif not netloc and p1.netloc == p2.netloc:
				service_url, reply_binding = _url, _binding
		return reply_binding, service_url

	def parse_saml_logout(self, client):
		binding, message, relay_state = self._get_saml_message(client)
		if message is None:
			return

		try:
			# WORKAROUND to detect what kind of logout request this is :/
			is_logout_request = 'LogoutRequest' in zlib.decompress(message.decode('base64'), -15).split('>', 1)[0]
		except Exception:
			is_logout_request = False

		if is_logout_request:
			return SamlLogoutRequest(message, binding, relay_state)
		return SamlLogoutResponse(message, binding)

	@handler('saml_logout_request')
	def handle_logout_request(self, name_id, request):
		"""Handles <SamlLogoutRequest> and returns a appropriate HTTP response"""
		http_args = self.sp.handle_logout_request(request.message, name_id, request.binding, relay_state=request.relay_state)
		return SamlHTTPResponse(http_args, request.binding)

	@handler('saml_logout_response')
	def handle_logout_response(self, response):
		"""Handles <SamlLogoutResponse>"""
		response = self.sp.parse_logout_request_response(response.message, response.binding)
		self.sp.handle_logout_response(response)

	@handler('saml_global_logout')
	def logout(self, name_id):
		"""Handles a request to logout and returns appropriate HTTP response in case logout needs to be done at the identity provider"""
		# what if more than one?
		try:
			data = self.sp.global_logout(name_id)
		except KeyError:
			tb = sys.exc_info()[2]
			while tb.tb_next:
				tb = tb.tb_next
			if tb.tb_frame.f_code.co_name != 'entities':
				raise
			# either the user was already logged out or this service was restarted meanwhile
			return

		for entity_id, logout_info in data.items():
			if not isinstance(logout_info, tuple):
				continue  # result from logout, should be OK

			binding, http_args = logout_info
			if binding not in (BINDING_HTTP_POST, BINDING_HTTP_REDIRECT):
				raise SamlError().unknown_logout_binding(binding)

			return SamlHTTPResponse(http_args, binding)

	def _get_saml_message(self, client):
		"""Get the SAML message and corresponding binding from the HTTP request"""
		if client.request.method not in (u'GET', u'POST'):
			raise METHOD_NOT_ALLOWED('GET, HEAD, POST')

		if client.request.method == u'GET':
			binding = BINDING_HTTP_REDIRECT
			args = dict(client.request.uri.query)
		elif client.request.method == u'POST':
			binding = BINDING_HTTP_POST
			args = dict(client.request.body.data)

		relay_state = args.get('RelayState', '')
		try:
			message = args['SAMLResponse']
		except KeyError:
			try:
				message = args['SAMLRequest']
			except KeyError:
				try:
					message = args['SAMLart']
				except KeyError:
					return None, None, None
				message = self.sp.artifact2message(message, 'spsso')
				binding = BINDING_HTTP_ARTIFACT

		return binding, message, relay_state
