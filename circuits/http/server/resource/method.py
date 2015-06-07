# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

import httoop


def method(func=None, http_method=None):
	def _decorator(method):
		return Method(method, http_method or func.__name__)

	if func is None:
		return _decorator
	return _decorator(func)


class Method(object):

	def __init__(self, method, http_method):
		self.http_method = http_method
		self.method = method
		self.safe = httoop.Method(self.http_method).safe
		self.idempotent = httoop.Method(self.http_method).idempotent
		self.content_types = {}
		self.content_languages = {}

	@classmethod
	def is_method(cls, member):
		return isinstance(member, Method)
