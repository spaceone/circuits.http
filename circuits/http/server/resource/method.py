# -*- coding: utf-8 -*-

from __future__ import absolute_import

import inspect

from circuits import BaseComponent
from circuits.http.utils import allof

from httoop import Method as _htMethod, FORBIDDEN
from httoop.codecs import Codec as _htCodec, lookup as codec_lookup


def method(func=None, http_method=None, **kwargs):
	if isinstance(func, (bytes, unicode)) and http_method is None:
		http_method = func
		func = None

	def _decorator(method):
		return Method(method, http_method or func.__name__, **kwargs)

	if func is None:
		return _decorator
	return _decorator(func)


class Method(object):  # TODO: minimize

	@property
	def available_mimetypes(self):
		return [m[1] for m in sorted(((codec_priority[1], mimetype) for mimetype, codec_priority in self.content_types.items()), reverse=True)]

	@property
	def resource(self):
		return self._resource

	@resource.setter
	def resource(self, resource):
		self.__class__ = type('Method', (type(self), BaseComponent), {})
		BaseComponent.__init__(self, channel=resource.channel)
		self.register(resource)
		#self._resource = resource  # FIXME: recursion error: circuits trys to register instance members which are components

	def __init__(self, method, http_method, **kwargs):
		self.http_method = http_method
		self.method = method
		self.safe = _htMethod(self.http_method).safe
		self.idempotent = _htMethod(self.http_method).idempotent
		self.coroutine = kwargs.get('coroutine', inspect.isgeneratorfunction(method))

		self.content_types = {}
		self.content_type_params = {}

		self.request_content_types = {}
		self.request_content_type_params = {}

		self._resource = None
		self._conditions = []

	def __call__(self, client, *args, **kwargs):
		if not allof(*self._conditions)(client):
			raise FORBIDDEN()
		return self.method(self.parent, client, *args, **kwargs)

	def conditions(self, *conditions):
		# TODO: make it possible to detect methods when using this as decorator (a function is passed)
		self._conditions.extend(conditions)

	def accept(self, mimetype, quality=1.0, **params):
		mime_codec = codec_lookup(mimetype, raise_errors=False)
		self.add_accept_codec(mime_codec, mimetype, quality, **params)

		def _decorator(codec):
			self.add_accept_codec(codec, mimetype, quality, **params)
			return codec
		return _decorator

	def codec(self, mimetype, quality=1.0, **params):
		"""Add a codec to the method. This method is eiter a decorator to add a function which acts as codec.
			Alternatively the codec from httoop is looked up.

			>>> class MyResource(Resource):
			... 	@method
			... 	def GET(self, client):
			... 		return some_data
			...
			... 	GET.codec('application/json', quality=0.5)  # add httoop default codec
			... 	@GET.codec('text/html', quality=1.0, charset='utf-8')  # implement own codec
			... 	def _get_html(self, client):
			... 		return b'<html>%s</html>' % (client.data,)
		"""
		mime_codec = codec_lookup(mimetype, raise_errors=False)
		self.add_codec(mime_codec, mimetype, quality, **params)

		def _decorator(codec):
			self.add_codec(codec, mimetype, quality, **params)
			return codec
		return _decorator

	def encode(self, client):
		if 'Content-Type' not in client.response.headers:
			return
		content_type = client.response.headers.element('Content-Type')
		mimetype = content_type.mimetype
		try:
			codec, quality = client.method.content_types[mimetype]
		except KeyError:
			return
		content_type.params.update(self.content_type_params[mimetype])
		client.response.headers['Content-Type'] = bytes(content_type)  # FIXME: python3
		client.response.body = codec(self.parent, client)

	def decode(self, client):
		if 'Content-Type' not in client.request.headers:
			return
		content_type = client.request.headers.element('Content-Type')
		mimetype = content_type.mimetype
		try:
			codec, quality = client.method.request_content_types[mimetype]
		except KeyError:
			return
		client.request.body.data = codec(self.parent, client)

	def add_codec(self, codec, mimetype, quality, **params):
		_codec = codec
		if isinstance(codec, _htCodec) or isinstance(codec, type) and issubclass(codec, _htCodec):
			def _codec(resource, client):
				return codec.encode(client.data)
				#client.response.body.codec = codec
				#client.response.body.encode()
		self.content_types[mimetype] = (_codec, quality)
		self.content_type_params[mimetype] = params

	def add_accept_codec(self, codec, mimetype, quality, **params):
		_codec = codec
		if isinstance(codec, _htCodec) or isinstance(codec, type) and issubclass(codec, _htCodec):
			def _codec(resource, client):
				body = client.request.body.read()  # FIXME: don't load into RAM
				return codec.decode(body)
		self.request_content_types[mimetype] = (_codec, quality)
		self.request_content_type_params[mimetype] = params

	def content_type_negotiation(self, client):
		accepted_mimetypes = dict((e.value, e.quality) for e in client.request.headers.elements('Accept')) or {u'*/*': 1}
		available_mimetypes = client.method.available_mimetypes
		if not available_mimetypes:
			return
		for mimetype in available_mimetypes:
			if accepted_mimetypes.get(mimetype):
				return mimetype
		for accepted in accepted_mimetypes:
			if accepted in (u'*', u'*/*'):
				for available in available_mimetypes:
					if accepted_mimetypes.get(available, 1):
						return available
			if accepted.endswith(u'/*'):
				for mimetype in available_mimetypes:
					if mimetype.startswith(accepted[:-1]) and accepted_mimetypes.get(mimetype, 1):
						return mimetype

	def content_language_negotiation(self, client):
		return ''

	@classmethod
	def is_method(cls, member):
		return isinstance(member, Method)
