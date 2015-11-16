# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import httphandler

from httoop import BAD_REQUEST, UNSUPPORTED_MEDIA_TYPE, PAYLOAD_TOO_LARGE, DecodeError


class RequestContentType(BaseComponent):

	@httphandler('request', priority=0.56)
	def check_maximum_payload_length(Self, client):
		if hasattr(client.resource, 'maximum_payload_length'):
			max_length = client.resource.maximum_payload_length(client)
			if max_length > len(client.request.body):
				raise PAYLOAD_TOO_LARGE('The request payload is too large. Maximum allowed length is %d bytes.' % (max_length,))

	@httphandler('request', priority=0.55)
	def decode_input_representation(self, client):

		if client.request.method.safe and client.request.body:
			# HTTP allows a GET / HEAD / ... request to have a request body
			# but it doesn't make sense and potencially opens security issues, so deny it here
			raise BAD_REQUEST('The request method is considered safe and cannot contain a request body.')

		content_type = client.request.headers.get('Content-Type')
		if not client.request.body:
			if content_type:
				raise BAD_REQUEST('Missing request body.')
			return

		if not content_type:
			raise BAD_REQUEST('Missing Content-Type header.')

		handler = client.request.headers.element('Content-Type').codec
		if not handler:
			raise UNSUPPORTED_MEDIA_TYPE('The request Content-Type %r is not supported.' % client.request.headers['Content-Type'])

		try:
			body = client.request.body.read()  # FIXME: don't load into RAM
			client.request.body.data = handler(client, body)
			client.request.body = client.request.body.data
		except DecodeError:
			raise BAD_REQUEST('Could not decode input representation.')
