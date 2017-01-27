# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

import inspect

from circuits import BaseComponent, handler
from circuits.http.utils import httphandler
from circuits.http.server.resource.method import Method
from circuits.http.server.caching import CacheControl, ETag, Expires, IfRange, LastModified, Vary, Pragma
from circuits.http.server.content import RequestContentType, ContentType, Security

from httoop import METHOD_NOT_ALLOWED, NOT_IMPLEMENTED


class Resource(BaseComponent):

	supported_methods = ('GET', 'HEAD', 'PUT', 'POST', 'DELETE', 'OPTIONS', 'TRACE', 'CONNECT')

	safe_methods = ()
	idempotent_methods = ()
	allowed_methods = ()

	default_features = [
		CacheControl, ETag, Expires, IfRange, LastModified, Vary, Pragma,
		RequestContentType, ContentType, Security
	]

	path = None

	def __init__(self, *args, **kwargs):
		super(Resource, self).__init__(*args, channel=kwargs.pop('channel', self.channel), **kwargs)
		self.path = self.path or self.channel
		self.methods = dict()
		self.routes = set()
		self.supported_methods = self.supported_methods
		self.safe_methods = self.safe_methods
		self.idempotent_methods = self.idempotent_methods
		self.children = set()
		self.default_features = self.default_features[:]
		self.acceptable_languages = set()
		self.acceptable = set()
		self.register_features()
		self.register_methods()

	def register_features(self):
		for FeatureType in self.default_features:
			FeatureType(channel=self.channel).register(self)

	def register_methods(self):
		for name, member in inspect.getmembers(self.__class__, Method.is_method):
			member.resource = self
			self.methods[member.http_method] = getattr(self, name)

		if 'GET' not in self.methods:
			raise RuntimeError('A HTTP resource must support a GET method.')

		self.methods.setdefault('HEAD', self.methods['GET'])
		self.allowed_methods = tuple(self.methods.keys())

	@handler('registered', channel='*')
	def _add_resource(self, resource, parent):
		if parent is self and isinstance(resource, Resource):
			self.children.add(resource)

	@handler('unregistered', channel='*')
	def _remove_resource(self, resource, parent):
		if parent is self and isinstance(resource, Resource):
			self.children.remove(resource)

	@httphandler('request', priority=1.0)
	def _pre_request(self, client):
		client.method = self.methods.get(client.request.method)

	@httphandler('request', priority=0.6)
	def _check_method_exists(self, client):
		if client.method is not None:
			return

		allow = u', '.join(self.allowed_methods)
		if client.request.method in self.supported_methods:
			raise METHOD_NOT_ALLOWED(allow, 'The specified method is invalid for this resource. Allowed methods are %s' % allow)
		raise NOT_IMPLEMENTED('The requested method is not implemented', headers=dict(Allow=allow))

	@httphandler('request', priority=0.5)
	def _execute_method(self, client):
		client.data = client.method(*self.positional_arguments(client), **self.keyword_arguments(client))
		client.method.encode(client)

	def keyword_arguments(self, client):
		return {}

	def positional_arguments(self, client):
		return (client,)

	def identify(self, client, path_segments):
		return True

	def etag(self, client):
		pass

	def last_modified(self, client):
		pass

	def content_language(self, client):
		return client.method.content_language_negotiation(client)

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
		return client.method.content_type_negotiation(client)
