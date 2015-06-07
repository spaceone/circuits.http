# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import sets_header, httphandler


class ContentType(BaseComponent):

	@httphandler('request', priority=0.4)
	@sets_header('Content-Type')
	def set_content_type(self, client):
		if hasattr(client.resource, 'content_type'):
			return client.resource.content_type(client)
