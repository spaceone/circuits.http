# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import allof

from httoop import Method as _htMethod, FORBIDDEN
from httoop.codecs import Codec as _htCodec, lookup as codec_lookup


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
		#self._resource = resource  # FIXME: recursion error

	def __init__(self, method, http_method):
		self.http_method = http_method
		self.method = method
		self.safe = _htMethod(self.http_method).safe
		self.idempotent = _htMethod(self.http_method).idempotent
		self.content_types = {}
		self._resource = None
		self._conditions = []

	def __call__(self, client):
		if not allof(*self._conditions)(client):
			raise FORBIDDEN()
		return self.method(client.resource, client)

	def conditions(self, *conditions):
		self._conditions.extend(conditions)

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
		self.add_codec(mime_codec, mimetype, quality, params)
		def _decorator(codec):
			self.add_codec(codec, mimetype, quality, params)
			return codec
		return _decorator

	def encode(self, client):
		if 'Content-Type' not in client.response.headers:
			return
		mimetype = client.response.headers.element('Content-Type').mimetype
		try:
			codec, quality = client.method.content_types[mimetype]
		except KeyError:
			return
		client.response.body = codec(client.resource, client)

	def add_codec(self, codec, mimetype, quality, params):
		_codec = codec
		if isinstance(codec, _htCodec) or isinstance(codec, type) and issubclass(codec, _htCodec):
			def _codec(resource, client):
				return codec.encode(client.data)
				client.response.body.codec = codec
				client.response.body.encode()
		self.content_types[mimetype] = (_codec, quality)

	def content_type_negotiation(self, client):
		# TODO: optimize a lot, find a nice algorithm!
		accepted_mimetypes = client.request.headers.values('Accept')
		available_mimetypes = client.method.available_mimetypes
		if not available_mimetypes:
			return
		for mimetype in available_mimetypes:
			if mimetype in accepted_mimetypes:
				return mimetype
		for accepted in accepted_mimetypes:
			if accepted in ('*', '*/*'):
				return available_mimetypes[0]
			if accepted.endswith('/*'):
				for mimetype in available_mimetypes:
					if mimetype.startswith(accepted[:-1]):
						return mimetype

	def content_language_negotiation(self, client):
		return

	@classmethod
	def is_method(cls, member):
		return isinstance(member, Method)
