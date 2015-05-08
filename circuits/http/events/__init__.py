# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import Event


class HTTPError(Event):
	"""HTTPError event

		args: (client, httperror)
	"""
	success = True
	failure = True

	def __init__(self, client, httperror):
		super(HTTPError, self).__init__(client, httperror)
		self.client = client
		self.httperror = httperror


class request(Event):
	"""Request event

		args: (client,)
	"""
	success = True
	failure = True


class response(Event):
	"""Response event

		args: (client,)
	"""
	success = True
	failure = True


class routing(Event):
	"""Routing event

		args: (client,)
	"""
	success = True
	failure = True
