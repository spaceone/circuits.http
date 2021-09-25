# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from httoop import NOT_ACCEPTABLE

from circuits import BaseComponent
from circuits.http.utils import httphandler, sets_header


class ContentLanguage(BaseComponent):

	@httphandler('request', priority=0.58)
	@sets_header('Content-Language')
	def set_content_language(self, client):
		if hasattr(client.resource, 'content_language'):
			language = client.resource.content_language(client)
			if language is None:
				raise NOT_ACCEPTABLE('The resource is not available in the requested Content-Language.')
			return language or None
