# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent

from httoop import Method as _htMethod
from httoop.codecs import Codec as _htCodec


def method(func=None, http_method=None):
	def _decorator(method):
		return Method(method, http_method or func.__name__)

	if func is None:
		return _decorator
	return _decorator(func)


class Method(object):

	@property
	def available_mimetypes(self):
		return [m[1] for m in sorted((codec_priority[1], mimetype) for mimetype, codec_priority in self.content_types.items())]

	@property
	def resource(self):
		return self._resource

	@resource.setter
	def resource(self, resource):
		self.__class__ = type(b'Method', (type(self), BaseComponent), {})
		BaseComponent.__init__(self, channel=resource.channel)
		self.register(resource)
		self._resource = resource

	def __init__(self, method, http_method):
		self.http_method = http_method
		self.method = method
		self.safe = _htMethod(self.http_method).safe
		self.idempotent = _htMethod(self.http_method).idempotent
		self.content_types = {}
		self._resource = None

	def __call__(self, client):
		return self.method(self._resource, client)

	def codec(self, mimetype, quality=1.0):
		def _decorator(codec):
			self.add_codec(codec, mimetype, quality)
			return codec
		return _decorator

	def add_codec(self, codec, mimetype, quality):
		_codec = codec
		if isinstance(codec, _htCodec):
			def _codec(resource, client):
				client.response.body.codec = codec
				client.response.body.encode()
		self.content_types[mimetype] = (_codec, quality)

	def content_type_negotiation(self, client):
		# TODO: optimize a lot, find a nice algorithm!
		accepted_mimetypes = client.request.headers.values('Accept')
		available_mimetypes = client.method.available_mimetypes
		for mimetype in available_mimetypes:
			if mimetype in accepted_mimetypes:
				return mimetype
		for accepted in accepted_mimetypes:
			if accepted in ('*', '*/*'):
				return available_mimetypes and available_mimetypes[0]
			if accepted.endswith('/*'):
				for mimetype in available_mimetypes:
					if mimetype.startswith(accepted[:-1]):
						return mimetype

	@classmethod
	def is_method(cls, member):
		return isinstance(member, Method)
