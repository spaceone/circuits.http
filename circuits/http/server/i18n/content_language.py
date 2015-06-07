# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import sets_header, httphandler


class ContentLanguage(BaseComponent):

	@httphandler('request', priority=0.59)
	@sets_header('Content-Language')
	def set_content_language(self, client):
		if hasattr(client.resource, 'language'):
			return client.resource.content_language()
