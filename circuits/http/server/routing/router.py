# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.events import response, request
from circuits.http.utils import httphandler

from httoop import NOT_FOUND, FORBIDDEN


class Router(BaseComponent):

	@httphandler('routing_success')
	def _on_routing_success(self, evt, result):
		if not evt.stopped:
			client = evt.args[0]
			channels = [c.channel for c in (client.domain, client.resource) if c is not None]
			if client.events.request:
				return
			client.events.request = self.fire(request(client), *channels).event

	@httphandler('request_success')
	def _on_request_success(self, evt, result):
		if not evt.stopped and not getattr(evt, '_request_success_foobar', None):
			evt._request_success_foobar = True  # FIXME: it seems this handler is called twice (for each channel?)
			client = evt.args[0]
			self.fire(response(client), client.server.channel)

	@httphandler('routing', priority=-0.12)
	def _on_resource_routing(self, client):
		if client.resource is None:
			if client.request.method in ('PUT', 'POST'):
				raise FORBIDDEN()
			raise NOT_FOUND(client.request.uri.path)
