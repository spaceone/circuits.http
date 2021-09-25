# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from circuits import BaseComponent
from circuits.http.utils import httphandler, if_header_set, sets_header


class AcceptEncoding(BaseComponent):

	@httphandler('request', priority=0.42)
	@if_header_set('Accept-Encoding')
	@sets_header('Content-Encoding')
	def set_content_encoding(self, client):
		if hasattr(client.resource, 'content_encoding'):
			return client.resource.content_encoding(client)
