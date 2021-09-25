# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from circuits import BaseComponent
from circuits.http.utils import httphandler, sets_header


class Vary(BaseComponent):

	@httphandler('request', priority=0.40)
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
		if 'Content-Encoding' in client.response.headers:
			vary += 'Accept-Encoding'
		return ', '.join(vary)  # TODO: return list
