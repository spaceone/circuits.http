# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.http.events import routing, response, request
from circuits.http.utils import httperror

from httoop import BAD_REQUEST


class Router(BaseComponent):

	@handler('request')
	def _on_request(self, client):
		event = routing(client)
		self.fire(event)
		yield #self.wait(event)  # FIXME: the following request event is fired twice then (handlers are executed twice)

		channels = [c.channel for c in (client.domain, client.resource) if c is not None]
		client.events.request = self.fire(request(client), *channels).event
		yield #self.wait(client.events.request)  # FIXME: circuits does no further event processing :/

		self.fire(response(client))

	@handler('routing', priority=-0.1)
	@httperror
	def _on_routing(self, client):
		if client.domain is None:
			# TODO: create a exception for this, so that implementors can give
			# alternative host links
			UnknownHost = lambda: BAD_REQUEST('The requested Host is unknown.')
			raise UnknownHost()
