# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.http.utils import sets_header


class ContentLanguage(BaseComponent):

	@handler('request', priority=0.59)
	@sets_header('Content-Language')
	def set_content_language(self, client):
		if hasattr(client.resource, 'language'):
			return client.resource.language()
