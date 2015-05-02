# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.http.utils import if_header_set

from httoop import EXPECTATION_FAILED


class IfRange(BaseComponent):

	@handler('request', priority=0.31)
	@if_header_set(('If-Range', 'Range'))
	def if_range(self, client):
		if_range = client.request.headers.get('If-Range')
		if 'Etag' in client.response.headers:
			etag = client.response.headers.element('ETag')
			if etag == if_range:
				return

		if 'Last-Modified' in client.response.headers:
			last_modified = client.response.headers.element('Last-Modified')
			if last_modified == if_range:
				return

		raise EXPECTATION_FAILED('If-Range not satisfiable.')
