# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.events import routing, response, request
from circuits.http.utils import httphandler

from httoop import BAD_REQUEST, NOT_FOUND, FORBIDDEN


class Router(BaseComponent):

	@httphandler('request')
	def _on_request(self, client):
		event = self.fire(routing(client), '*').event  # TODO: separate domain/resource routing to prevent '*'
		yield self.wait(event, event.channels)
		if event.stopped:
			return

		channels = [c.channel for c in (client.domain, client.resource) if c is not None]
		if not channels:
			return

		event = client.events.request = self.fire(request(client), *channels).event
		yield self.wait(event, *channels)

		if event.stopped:
			return
		self.fire(response(client))

	@httphandler('routing', priority=-0.11)
	def _on_domain_routing(self, client):
		if client.domain is None:
			# TODO: create a exception for this, so that implementors can give
			# alternative host links
			# TODO: Implement ExposeDomains component
			UnknownHost = lambda: BAD_REQUEST('The requested Host is unknown.')
			raise UnknownHost()

	@httphandler('routing', priority=-0.12)
	def _on_resource_routing(self, client):
		if client.resource is None:
			if client.request.method in ('PUT', 'POST'):
				raise FORBIDDEN()
			raise NOT_FOUND(client.request.uri.path)
