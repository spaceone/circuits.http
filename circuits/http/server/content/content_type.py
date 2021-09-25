# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from httoop import NOT_ACCEPTABLE
from httoop.header import Accept

from circuits import BaseComponent
from circuits.http.utils import httphandler, sets_header


class ContentType(BaseComponent):

	@httphandler('request', priority=0.59)
	@sets_header('Content-Type')
	def set_content_type(self, client):
		if hasattr(client.resource, 'content_type'):
			return client.resource.content_type(client)

	@httphandler('request', priority=0.51)
	def _not_acceptable(self, client):
		if 'Content-Type' not in client.response.headers:
			for mimetype, (codec, quality) in client.method.content_types.items():
				accept = Accept(mimetype, {'q': quality})
				client.response.headers.append('Accept', bytes(accept))  # TODO: python3
			raise NOT_ACCEPTABLE('Available Content-Types are %r.' % (client.method.content_types.keys(),))
