# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.http.events import routing, response
from circuits.http.utils import httperror

from httoop import BAD_REQUEST


class Router(BaseComponent):

	@handler('request')
	def _on_request(self, client):
		yield self.wait(self.fire(routing(client)))
		channels = [c.channel for c in (client.domain, client.resource) if c is not None]
		yield self.wait(self.fire(request(client), channels=channels))
		self.fire(response(client))

	@handler('routing', priority=0)
	@httperror
	def _on_routing(self, client):
		if client.domain is None:
			# TODO: create a exception for this, so that implementors can give
			# alternative host links
			UnknownHost = lambda: BAD_REQUEST('The requested Host is unknown.')
			raise UnknownHost()

