# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.http.events import routing, response, request
from circuits.http.utils import httperror

from httoop import BAD_REQUEST, NOT_FOUND, FORBIDDEN


class Router(BaseComponent):

	@handler('request')
	def _on_request(self, client):
		event = routing(client)
		# FIXME: https://github.com/circuits/circuits/issues/60
		#self.fire(event)
		#yield #self.wait(event)  # FIXME: the following request event is fired twice then (handlers are executed twice)
		yield self.call(event)
		if event.stopped:
			return

		channels = [c.channel for c in (client.domain, client.resource) if c is not None]
		if not channels:
			return

		event = self.fire(request(client), *channels).event
		client.events.request = event  # make sure error handlers can stop the event
		# FIXME: https://github.com/circuits/circuits/issues/60
		yield #self.wait(client.events.request)  # FIXME: circuits does no further event processing :/

		if event.stopped:
			return
		self.fire(response(client))

	@handler('routing', priority=-0.11)
	@httperror
	def _on_domain_routing(self, client):
		if client.domain is None:
			# TODO: create a exception for this, so that implementors can give
			# alternative host links
			UnknownHost = lambda: BAD_REQUEST('The requested Host is unknown.')
			raise UnknownHost()

	@handler('routing', priority=-0.12)
	@httperror
	def _on_resource_routing(self, client):
		if client.resource is None:
			if client.request.method in ('PUT', 'POST'):
				raise FORBIDDEN()
			raise NOT_FOUND(client.request.uri.path)
