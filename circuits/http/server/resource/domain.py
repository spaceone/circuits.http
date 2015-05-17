# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.http.server.resource.resource import Resource

from httoop import URI


class Domain(BaseComponent):

	def __init__(self, fqdn):
		super(Domain, self).__init__(channel=fqdn.lower())
		self.fqdn = self.channel
		self.aliases = set()
		self.resources = set()
		self.dispatchers = set()

	@handler('registered', channel='*')
	def _add_resource(self, resource, parent):
		if parent is self and isinstance(resource, Resource):
			self.resources.add(resource)

	@handler('unregistered', channel='*')
	def _remove_resource(self, resource, parent):
		if parent is self and isinstance(resource, Resource):
			self.resources.remove(resource)

	def url(self, client, *path):
		uri = URI(scheme=client.request.scheme, host=self.fqdn, port=client.server.port)
		uri.join(*path)
		return uri
