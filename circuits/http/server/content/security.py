# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import sets_header, httphandler


class Security(BaseComponent):

	@httphandler('request', priority=0.80)
	@sets_header('X-Frame-Options')
	def frame_options(self, client):
		if hasattr(client.resource, 'frame_options'):
			return client.resource.frame_options(client)

	@httphandler('request', priority=0.80)
	@sets_header('X-XSS-Protection')
	def xss_protection(self, client):
		if hasattr(client.resource, 'xss_protection'):
			return client.resource.xss_protection(client)

	@httphandler('request', priority=0.80)
	@sets_header('X-Content-Type-Options')
	def content_type_options(self, client):
		if hasattr(client.resource, 'content_type_options'):
			return client.resource.content_type_options(client)

	@httphandler('request', priority=0.80)
	@sets_header('Strict-Transport-Security')
	def strict_transport_security(self, client):
		if hasattr(client.resource, 'strict_transport_security') and client.request.uri.scheme == 'https':
			return client.resource.strict_transport_security(client)

	@httphandler('request', priority=0.80)
	@sets_header('Public-Key-Pins')
	def public_key_pins(self, client):
		if hasattr(client.resource, 'public_key_pins'):
			return client.resource.public_key_pins(client)

	@httphandler('request', priority=0.80)
	@sets_header('Content-Security-Policy')
	def content_security_policy(self, client):
		if hasattr(client.resource, 'content_security_policy'):
			return client.resource.content_security_policy(client)

	@httphandler('request', priority=0.80)
	@sets_header('Referrer-Policy')
	def referrer_policy(self, client):
		if hasattr(client.resource, 'referrer_policy'):
			return client.resource.referrer_policy(client)

	@httphandler('request', priority=0.80)
	@sets_header('Feature-Policy')
	def feature_policy(self, client):
		if hasattr(client.resource, 'feature_policy'):
			return client.resource.feature_policy(client)

	@httphandler('request', priority=0.80)
	@sets_header('X-Permitted-Cross-Domain-Policies')
	def permitted_cross_domain_policies(self, client):
		if hasattr(client.resource, 'permitted_cross_domain_policies'):
			return client.resource.permitted_cross_domain_policies(client)
