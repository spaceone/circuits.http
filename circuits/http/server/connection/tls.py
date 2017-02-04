# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.net.events import starttls, close, write
from circuits.http.utils import if_header_set, httphandler

from httoop import SWITCHING_PROTOCOLS, Response


class TLS(BaseComponent):

	@httphandler('request', priority=0.9)
	@if_header_set('Connection', with_event=True)
	@if_header_set('Upgrade', with_event=True)
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
