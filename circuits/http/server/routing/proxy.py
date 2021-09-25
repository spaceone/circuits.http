# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from circuits import BaseComponent
from circuits.http.utils import httphandler


class ReverseProxy(BaseComponent):

	def init(self, gateways=None, *args, **kwargs):
		if gateways is None:
			gateways = ('127.0.0.1', '::1')
		self.gateways = gateways

	@httphandler('routing', priority=2.0)
	def _on_routing(self, client):
		if client.remote.ip not in self.gateways:
			return

		for forwarded in client.request.headers.elements('Forwarded'):
			if not forwarded.by or any(forwarded.by == x[0] for x in self.gateways):
				client.remote.ip = forwarded.for_
				client.remote.name = None
				client.remote.resolve()
				if forwarded.proto in ('http', 'https'):
					client.request.uri.scheme = forwarded.proto
				if forwarded.host:
					client.request.headers['Host'] = forwarded.host
				return

		for forwarded in client.request.headers.elements('X-Forwarded-For'):
			client.remote.ip = forwarded.value
			client.remote.name = None
			client.remote.resolve()
			proto = client.request.headers.elements('X-Forwarded-Proto')
			if proto and proto[0].value in ('http', 'https'):
				client.request.uri.scheme = proto[0].value
			hosts = client.request.headers.elements('X-Forwarded-Host')
			if hosts:
				client.request.headers['Host'] = hosts[0].value
			return
