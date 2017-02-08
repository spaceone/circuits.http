from saml2.response import VerificationError, UnsolicitedResponse, StatusError
from saml2.s_utils import UnknownPrincipal, UnsupportedBinding
from saml2.sigver import MissingKey, SignatureError
from saml2 import BINDING_HTTP_ARTIFACT, BINDING_HTTP_REDIRECT


class SamlAuthnRequest(object):

	def __init__(self, relay_state=None, state=None, is_passive=False, service_provider_url=None, reply_binding=None, preferred_identity_provider=None, **kwargs):
		self.relay_state = relay_state
		self.state = state
		self.is_passive = is_passive
		self.service_provider_url = service_provider_url
		self.reply_binding = reply_binding
		self.preferred_identity_provider = preferred_identity_provider
		self.kwargs = kwargs


class SamlAuthnResponse(object):

	def __init__(self, response, binding, message, relay_state):
		self.response = response
		self.name_id = self.response.name_id
		self.attributes = self.response.ava
		self.binding = binding
		self.message = message
		self.relay_state = relay_state

	def __repr__(self):
		return '<samlp:Response name_id=%r attributes=%r>' % (self.name_id, self.attributes)


class SamlLogoutRequest(object):

	def __init__(self, message, binding, relay_state):
		self.message = message
		self.binding = binding
		self.relay_state = relay_state


class SamlLogoutResponse(object):

	def __init__(self, message, binding):
		self.message = message
		self.binding = binding


class SamlHTTPResponse(object):

	def __init__(self, http_args, binding):
		self.http_args = http_args
		self.binding = binding

	def apply(self, client):
		body = ''.join(self.http_args["data"])
		for key, value in self.http_args["headers"]:
			client.response.headers[key] = value

		if self.binding in (BINDING_HTTP_ARTIFACT, BINDING_HTTP_REDIRECT):
			client.response.status = 303 if client.request.protocol >= (1, 1) and client.request.method == u'POST' else 302

		client.response.body = body
		return client.response.body


class SamlError(Exception):

	message = None

	def __init__(self, message=None):
		self.message = message or self.message
		super(SamlError, self).__init__(self.message)

	@classmethod
	def from_exception(cls, exc):
		if isinstance(exc, UnknownPrincipal):
			message = cls.unknown_principal(exc)
		elif isinstance(exc, UnsupportedBinding):
			message = cls.unsupported_binding(exc)
		elif isinstance(exc, VerificationError):
			message = cls.verification_error(exc)
		elif isinstance(exc, UnsolicitedResponse):
			message = cls.unsolicited_response(exc)
		elif isinstance(exc, StatusError):
			message = cls.status_error(exc)
		elif isinstance(exc, MissingKey):
			message = cls.missing_key(exc)
		elif isinstance(exc, SignatureError):
			message = cls.signature_error(exc)
		else:
			message = str(exc)
		raise cls(message)

	@classmethod
	def unknown_principal(cls, exc):
		return ('The principal is unknown: %s') % (exc,)

	@classmethod
	def unsupported_binding(cls, exc):
		return ('The requested SAML binding is not known: %s') % (exc,)

	@classmethod
	def unknown_logout_binding(cls, binding):
		return ('The logout binding is not known.')

	@classmethod
	def verification_error(cls, exc):
		return ('The SAML response could not be verified: %s') % (exc,)

	@classmethod
	def unsolicited_response(cls, exc):
		return ('Received an unsolicited SAML response. Please try to single sign on again. Error message: %s') % (exc,)

	@classmethod
	def status_error(cls, exc):
		return ('The identity provider reported a status error: %s') % (exc,)

	@classmethod
	def missing_key(cls, exc):
		return ('The issuer %r is now known to the SAML service provider. This is probably a misconfiguration and might be resolved by restarting the service. Contact an administrator.') % (str(exc),)

	@classmethod
	def signature_error(cls, exc):
		return ('The SAML response contained a invalid signature: %s') % (exc,)


class EmptyAuthnResponse(SamlError):
	message = "The SAML message is invalid for this service provider."


class NoIdentityProvider(SamlError):
	message = 'There is a configuration error in the service provider: No identity provider are set up for use.'


class MultipleIdentityProvider(SamlError):

	def __init__(self, idps):
		super(MultipleIdentityProvider, self).__init__('Could not pick an identity provider. Please select one of %(idps)r' % {'idps': idps})
		self.idps = idps
