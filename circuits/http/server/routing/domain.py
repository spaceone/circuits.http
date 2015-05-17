# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.http.utils import httperror
from circuits.http.server.resource import Domain

from httoop import BAD_REQUEST, MOVED_PERMANENTLY
from httoop.header import Host


class DomainRouter(BaseComponent):

	use_x_forwarded_host = True

	def __init__(self, channel):
		super(DomainRouter, self).__init__(channel=channel)
		self.domains = set()

	@handler('routing', priority=1.9)
	def _http_one_zero(self, client):
		# HTTP 1.0 does not contain Host-header
		if client.request.protocol <= (1, 0):
			client.request.header['Host'] = client.local.host

	@handler('routing', priority=1.8)
	@httperror
	def _route_host(self, client):
		host = client.request.headers.element('Host')
		client.domain = self._get_domain(host, client)

	@handler('routing', priority=1.7)
	@httperror
	def _route_forwarded_host(self, client):
		if client.domain is not None or not self.use_x_forwarded_host:
			return

		for host in client.request.headers.elements('X-Forwarded-Host'):
			host = Host(host)
			domain = self._get_domain(host, client)
			if domain:
				client.domain = domain
				client.request.headers['Host'] = domain.fqdn
				return

	def _get_domain(self, host, client):
		hostname = host.hostname

		for domain in self.domains:
			if domain.fqdn == hostname:
				return domain
			if hostname in domain.aliases:
				return self.redirect_alias(domain, client)

	def redirect_alias(self, domain, client):
		path = domain.url(client, *client.request.path_segments)
		path.query = {}  # TODO: check if we MUST leave out querystring
		raise MOVED_PERMANENTLY(path)

	@handler('registered', channel='*')
	def _add_domain(self, domain, parent):
		if parent is self and isinstance(domain, Domain):
			self.domains.add(domain)

	@handler('unregistered', channel='*')
	def _remove_domain(self, domain, parent):
		if parent is self and isinstance(domain, Domain):
			self.domains.remove(domain)