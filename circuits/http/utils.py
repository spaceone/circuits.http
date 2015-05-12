# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits.http.events import HTTPError
from httoop import HTTPStatusException


def sets_header(header, ifmethod=None):
	def _decorator(func):
		def _decorated(self, client, *args, **kwargs):
			if ifmethod and client.method not in ifmethod:
				return
			value = func(self, client, *args, **kwargs)
			if value is not None:
				client.response.headers[header] = value
		return _decorated
	return _decorator


def if_header_set(header, ifmethod=None):
	def _decorator(func):
		def _decorated(self, client, *args, **kwargs):
			if ifmethod and client.method not in ifmethod:
				return
			if header in client.request.headers:
				return func(self, client, *args, **kwargs)
		return _decorated
	return _decorator


def httperror(func):
	def _decorated(self, event, client, *args, **kwargs):
		try:
			return func(self, client, *args, **kwargs)
		except HTTPStatusException as httperror:
			event.stop()
			self.fire(HTTPError(client, httperror))
	return _decorated
