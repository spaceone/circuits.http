# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import httphandler

from httoop import BAD_REQUEST, UNSUPPORTED_MEDIA_TYPE, PAYLOAD_TOO_LARGE, DecodeError
from httoop.header import Accept


class RequestContentType(BaseComponent):

	@httphandler('request', priority=0.56)
	def check_maximum_payload_length(self, client):
		if hasattr(client.resource, 'maximum_payload_length'):
			max_length = client.resource.maximum_payload_length(client)
			if max_length > len(client.request.body):
				raise PAYLOAD_TOO_LARGE('The request payload is too large. Maximum allowed length is %d bytes.' % (max_length,))

	@httphandler('request', priority=0.55)
	def decode_input_representation(self, client):
		content_type = client.request.headers.element('Content-Type')
		if not content_type and client.request.body:
			raise UNSUPPORTED_MEDIA_TYPE('Missing Content-Type header in request.')
		if client.request.method in (u'GET', u'HEAD') and client.request.body:
			raise BAD_REQUEST('The request method is considered safe and cannot contain a request body.')
		if not content_type:
			return

		if content_type.mimetype not in client.method.request_content_types:
			for mimetype, (codec, quality) in client.method.request_content_types.items():
				accept = Accept(mimetype, {'q': str(quality)})
				client.response.headers.append('X-Supported-Media-Types', bytes(accept))  # TODO: python3
			raise UNSUPPORTED_MEDIA_TYPE('The request Content-Type %r is not supported. Please use one of %r.' % (
				client.request.headers['Content-Type'],
				client.method.request_content_types.keys()
			))

		try:
			client.method.decode(client)
		except DecodeError:
			raise BAD_REQUEST('Could not decode input representation.')
