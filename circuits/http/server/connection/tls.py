# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from httoop import SWITCHING_PROTOCOLS, Response

from circuits import BaseComponent, handler
from circuits.http.utils import httphandler, if_header_set
from circuits.net.events import close, starttls, write


class TLS(BaseComponent):

	@httphandler('request', priority=0.9)
	@if_header_set('Connection')
	@if_header_set('Upgrade')
	def _on_request(self, event, client):
		request, response = client
		headers = request.headers

		if not headers.element('Connection').upgrade or not headers.element('Upgrade').tls:
			return

		data = Response(status=SWITCHING_PROTOCOLS().code)
		data.headers['Upgrade'] = '%s, %s' % (headers['Upgrade'], response.protocol)
		data.headers['Connection'] = 'Upgrade'
		data = b'%s%s' % (data, data.headers)
		self.fire(write(data, client.socket), client.server.channel)
		yield self.wait(starttls(client.socket))

	@handler('starttls_failure')
	def _on_starttls_failure(self, evt, error):
		socket = evt.args[0]
		self.fire(close(socket))
