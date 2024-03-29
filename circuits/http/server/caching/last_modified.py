# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from httoop import BAD_REQUEST, NOT_MODIFIED, PRECONDITION_FAILED, Date, InvalidDate

from circuits import BaseComponent
from circuits.http.utils import httphandler, if_header_set, sets_header


class LastModified(BaseComponent):

	@httphandler('request', priority=0.7)
	@sets_header('Last-Modified')
	def _last_modified_header(self, client):
		if hasattr(client.resource, 'last_modified'):
			last_modified = client.resource.last_modified(client)
			if not isinstance(last_modified, (type(None), Date)):
				last_modified = Date(last_modified)
			return last_modified

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
