# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler

from httoop import BAD_REQUEST, UNSUPPORTED_MEDIA_TYPE, DecodeError


class RequestContentType(BaseComponent):

	@handler('request', priority=0.45)
	def decode_input_representation(self, client):

		if client.method.safe and client.request.body:
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