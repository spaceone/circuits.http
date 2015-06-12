# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.http.server.resource.resource import Resource

from httoop import URI


class Domain(BaseComponent):

	RouterType = None

	def __init__(self, fqdn):
		super(Domain, self).__init__(channel=fqdn.lower())
		self.fqdn = self.channel
		self.aliases = set()
		self.children = set()
		self.dispatchers = set()

		self.register_routing()

	def register_routing(self):
		RouterType = self.RouterType
		if RouterType is None:
			from circuits.http.server.routing import RegexPathRouter as RouterType
		self.router = RouterType(channel=self.channel).register(self)

	@handler('registered', channel='*')
	def _add_resource(self, resource, parent):
		if parent is self and isinstance(resource, Resource):
			self.children.add(resource)

	@handler('unregistered', channel='*')
	def _remove_resource(self, resource, parent):
		if parent is self and isinstance(resource, Resource):
			self.children.remove(resource)

	def url(self, client, *path):
		uri = URI(scheme=client.request.scheme, host=self.fqdn, port=client.server.port)
		uri.join(*path)
		return uri
