# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import sets_header, if_header_set, httphandler

from httoop import PRECONDITION_FAILED, NOT_MODIFIED


class ETag(BaseComponent):

	@httphandler('request', priority=0.7)
	@sets_header('Etag')
	def _etag_header(self, client):
		if hasattr(client.resource, 'etag'):
			return client.resource.etag(client)

	@httphandler('request', priority=0.69)
	@if_header_set('If-None-Match')
	def _none_match(self, client):
		if 'Etag' in client.response.headers:
			none_match = client.request.headers['If-None-Match']
			etag = client.response.headers.element('Etag')

			if etag == none_match:
				# Conditional GET
				if client.request.method in ('GET', 'HEAD'):
					raise NOT_MODIFIED()
				raise PRECONDITION_FAILED()
		else:
			# FIXME: what should we do here?
			pass

	@httphandler('request', priority=0.69)
	@if_header_set('If-Match')
	def _match(self, client):
		# Conditional HTTP: ETag
		if 'Etag' in client.response.headers:
			if_match = client.request.headers['If-Match']
			etag = client.response.headers.element('Etag')
			if etag != if_match:
				raise PRECONDITION_FAILED()
		else:
			# FIXME: what should we do here?
			pass
