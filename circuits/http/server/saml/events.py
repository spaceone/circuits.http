from __future__ import absolute_import

from circuits import Event


class single_sign_on(Event):
	"""param request"""


class saml_logout_request(Event):
	"""param: name_id, request"""


class saml_logout_response(Event):
	"""param: response"""


class saml_global_logout(Event):

	def __init__(self, name_id):
		Event.__init__(self, name_id=name_id)
