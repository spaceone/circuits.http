# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import sets_header, if_header_set, httphandler

from httoop import InvalidDate, NOT_MODIFIED, BAD_REQUEST, PRECONDITION_FAILED


class LastModified(BaseComponent):

	@httphandler('request', priority=0.7)
	@sets_header('Last-Modified')
	def _last_modified_header(self, client):
		if hasattr(client.resource, 'last_modified'):
			return client.resource.last_modified(client)

	@httphandler('request', priority=0.6909)
	@if_header_set('If-Modified-Since', ifmethod=('GET', 'HEAD'))
	def conditional_get(self, client):
		if 'Last-Modified' not in client.response.headers:
			return

		last_modified = client.response.headers.element('Last-Modified')
		try:
			modified_since = client.request.headers.element('If-Modified-Since')
		except InvalidDate:
			raise BAD_REQUEST('Incorrect date format in If-Modified-Since header')
		if last_modified <= modified_since:
			raise NOT_MODIFIED()

	@httphandler('request', priority=0.6908)
	@if_header_set('If-Unmodified-Since')
	def unmodified_since(self, client):
		if 'Last-Modified' not in client.response.headers:
			raise PRECONDITION_FAILED('If-Unmodified-Since not satisfiable.')

		last_modified = client.response.headers.element('Last-Modified')

		try:
			unmodified_since = client.request.headers.element('If-Unmodified-Since')
		except InvalidDate:
			raise BAD_REQUEST('Incorrect date format in If-Unmodified-Since header')

		if last_modified > unmodified_since:
			raise PRECONDITION_FAILED('Resource has changed.')
