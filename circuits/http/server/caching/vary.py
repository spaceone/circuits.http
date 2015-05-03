# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.http.utils import sets_header


class Vary(BaseComponent):

	@handler('request', priority=0.60)
	@sets_header('Vary', ifmethod=('GET', 'HEAD', 'OPTIONS'))
	def _vary_header(self, client):
		if hasattr(client.resource, 'vary'):
			return client.resource.vary(client)

	# TODO: move this method into the resource base class
	def vary(self, client):
		u"""Sets the Vary-header depending on which response headers are set"""
		vary = ['Accept', 'Accept-Language']
		if getattr(client.method, 'conditions', None):
			vary += ['WWW-Authenticate']
		if 'ETag' in client.response.headers:
			vary += ['If-Match', 'If-None-Match']
		if 'Last-Modified' in client.response.headers:
			vary += ['If-Modified-Since', 'If-Unmodified-Since']
		return ', '.join(vary)