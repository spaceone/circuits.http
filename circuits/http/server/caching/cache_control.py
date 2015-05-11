# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.http.utils import sets_header


class CacheControl(BaseComponent):

	@handler('request', priority=0.4)
	@sets_header('Cache-Control', ifmethod=('GET', 'HEAD', 'OPTIONS'))
	def set_cache_control_header(self, client):
		if hasattr(client.resource, 'cache_control'):
			return client.resource.cache_control(client)
