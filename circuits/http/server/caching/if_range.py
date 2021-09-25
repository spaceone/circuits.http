# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from httoop import EXPECTATION_FAILED, Date, InvalidDate

from circuits import BaseComponent
from circuits.http.utils import httphandler, if_header_set


class IfRange(BaseComponent):

	@httphandler('request', priority=0.69)
	@if_header_set(('If-Range',))
	def if_range(self, client):
		if 'Range' not in client.request.headers:
			return
		if_range = client.request.headers.get('If-Range')
		if 'Etag' in client.response.headers:
			etag = client.response.headers.element('ETag')
			if etag == if_range:
				return

		if 'Last-Modified' in client.response.headers:
			last_modified = client.response.headers.element('Last-Modified')
			try:
				Date(if_range)
			except InvalidDate:
				pass
			else:
				if last_modified == if_range:
					return

		raise EXPECTATION_FAILED('If-Range not satisfiable.')
