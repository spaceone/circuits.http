# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

import inspect

from circuits import BaseComponent
from circuits.http.utils import httphandler
from circuits.http.server.resource.method import Method
from circuits.http.server.caching import CacheControl, ETag, Expires, IfRange, LastModified, Vary
from circuits.http.server.content import RequestContentType

from httoop import METHOD_NOT_ALLOWED, NOT_IMPLEMENTED


class Resource(BaseComponent):

	supported_methods = ('GET', 'HEAD', 'PUT', 'POST', 'DELETE', 'OPTIONS', 'TRACE', 'CONNECT')

	safe_methods = ()
	idempotent_methods = ()
	allowed_methods = ()

	default_features = [
		CacheControl, ETag, Expires, IfRange, LastModified, Vary,
		RequestContentType
	]

	def __init__(self, channel=None):
		super(Resource, self).__init__(channel=channel or self.channel)
		self.path = None
		self.methods = dict()
		self.supported_methods = self.supported_methods
		self.safe_methods = self.safe_methods
		self.idempotent_methods = self.idempotent_methods
		self.children = []
		self.default_features = self.default_features[:]
		self.acceptable_languages = set()
		self.acceptable = set()
		self.register_routing()
		self.register_features()
		self.register_methods()

	def register_routing(self):
		pass

	def register_features(self):
		for FeatureType in self.default_features:
			FeatureType(channel=self.channel).register(self)

	def register_methods(self):
		for name, member in inspect.getmembers(self.__class__, Method.is_method):
			member.__class__ = type(b'%sMethod' % (name,), (Method, BaseComponent), {})
			BaseComponent.__init__(member, channel=self.channel)
			member.register(self)
			self.methods[member.http_method] = member

		if 'GET' not in self.methods:
			raise RuntimeError('A HTTP resource must support a GET method.')

		self.methods.setdefault('HEAD', self.methods['GET'])
		self.allowed_methods = tuple(self.methods.keys())

	@httphandler('request', priority=0.5)
	def _check_method_exists(self, client):
		if client.method is not None:
			return

		allow = ', '.join(self.allowed_methods)
		if client.request.method in self.supported_methods:
			raise METHOD_NOT_ALLOWED(allow, 'The specified method is invalid for this resource. Allowed methods are %s' % allow)
		raise NOT_IMPLEMENTED('The requested method is not implemented', headers=dict(Allow=allow))

	def etag(self, client):
		pass

	def last_modified(self, client):
		pass

	def content_language(self, client):
		pass

	def cache_control(self, client):
		pass

	def vary(self, client):
		pass

	def expires(self, client):
		pass

	def location(self, client):
		pass

	def content_location(self, client):
		pass

	def content_type(self, client):
		pass
