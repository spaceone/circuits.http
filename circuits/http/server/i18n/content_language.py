# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import sets_header, httphandler

from httoop import NOT_ACCEPTABLE


class ContentLanguage(BaseComponent):

	@httphandler('request', priority=0.58)
	@sets_header('Content-Language')
	def set_content_language(self, client):
		if hasattr(client.resource, 'content_language'):
			language = client.resource.content_language()
			if language == '':
				raise NOT_ACCEPTABLE('The resource is not available in the requested Content-Language.')
			return language
