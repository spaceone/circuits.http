# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

import os
import mimetypes
from errno import EACCES, ENOENT

from circuits.http.server.resource.resource import Resource
from circuits.http.server.resource.method import method
from circuits.http.utils import httphandler

from httoop import FORBIDDEN, NOT_FOUND, Date

try:
	import magic
except ImportError:
	magic = None


class StaticResource(Resource):

	def __init__(self, *args, **kwargs):
		super(StaticResource, self).__init__(*args, **kwargs)
		self.GET.encode = self.encode

	def encode(self, client):
		return

	def identify(self, client, path_segments):
		basedir = os.path.abspath(self.directory(client))
		path = os.path.abspath(os.path.join(basedir, path_segments.get('path', '')))

		if not os.path.isfile(path) or not path.startswith(basedir):
			return False
		client.filename = path
		return True

	def directory(self, client):
		return ''

	@httphandler('request', priority=0.9)
	def __on_request(self, client):
		try:
			client.response.body = open(client.filename, 'rb')
		except IOError as exc:
			if exc.errno == EACCES:
				raise FORBIDDEN()
			if exc.errno == ENOENT:
				raise NOT_FOUND(client.request.uri.path)
			raise

	@method
	def GET(self, client):
		return client.response.body.fd

	def last_modified(self, client):
		try:
			return Date(os.stat(client.response.body.name).st_mtime)
		except (IOError, OSError):
			pass

	def content_type(self, client):
		if client.request.method != 'GET':
			return super(StaticResource, self).content_type(client)

		mimetype, acceptable = None, set(['*', '*/*'])
		accept = set(client.request.headers.values('Accept'))
		_, ext = os.path.splitext(client.filename)
		if ext:
			mimetype = mimetypes.types_map.get(ext)
			if mimetype:
				acceptable.add(mimetype)
				acceptable.add('%s/*' % mimetype.split('/', 1)[0])
		if not mimetype:
			if hasattr(magic, 'from_file'):
				mimetype = magic.from_file(client.filename, mime=True)
			elif magic:
				m = magic.open(magic.MAGIC_MIME)
				m.load()
				mimetype = m.file(client.filename)
		if accept and not accept & acceptable:
			return  # not acceptable
		return mimetype
