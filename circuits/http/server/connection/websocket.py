# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import base64
import hashlib

from httoop import BAD_REQUEST, SWITCHING_PROTOCOLS

from circuits import BaseComponent, handler
from circuits.http.events import response as RE
from circuits.http.utils import httphandler, if_header_set
from circuits.net.events import connect, disconnect
from circuits.protocols.websocket import WebSocketCodec


class Websocket(BaseComponent):

	def __init__(self, wschannel, *args, **kwargs):
		super(Websocket, self).__init__(*args, **kwargs)
		self._wschannel = wschannel or '%s-websocket' % (self.channel,)
		self._codecs = {}

	@httphandler('request', priority=0.8)
	@if_header_set('Upgrade', with_event=True)
	def _on_request(self, event, client):

		request, response = client
		headers = request.headers

		if not headers.element('Upgrade').websocket:
			return

		sec_key = headers.get('Sec-WebSocket-Key', u'').encode('utf-8')
		subprotocols = headers.elements("Sec-WebSocket-Protocol")

		def _valid_websocket_request():
			yield 'Host' in headers
			yield any(x.upgrade for x in headers.elements('Connection'))
			yield bool(sec_key)
			try:
				yield len(base64.b64decode(sec_key)) == 16
			except ValueError:
				yield False

		if not all(_valid_websocket_request()):
			raise BAD_REQUEST('Upgrading the connection to websocket requires a Sec-WebSocket-Key, upgrade connection token and host header to be set.')

		websocket_version = '13'
		if headers.get('Sec-WebSocket-Version', '') != websocket_version:
			response.headers['Sec-WebSocket-Version'] = websocket_version
			raise BAD_REQUEST('Sec-WebSocket-Version != %s not supported' % (websocket_version,))

		# Generate accept header information
		msg = b'%s258EAFA5-E914-47DA-95CA-C5AB0DC85B11' % (sec_key,)
		accept = base64.b64encode(hashlib.sha1(msg).digest()).decode('ascii')

		# Successful completion
		response.status = SWITCHING_PROTOCOLS().code
		response.close = False  # FIXME: remove this connection from HTTP component
		# TODO: logic should be handled by httoop
		response.headers.pop('Content-Type', None)
		response.headers['Upgrade'] = 'WebSocket'
		response.headers['Connection'] = 'Upgrade'
		response.headers['Sec-WebSocket-Accept'] = accept
		if subprotocols:
			response.headers["Sec-WebSocket-Protocol"] = self.select_subprotocol(subprotocols)
		response.body = ['WebSocket Protocol Handshake']

		codec = WebSocketCodec(client.socket, channel=self._wschannel)
		codec.register(client.server.socket)
		self._codecs[client.socket] = codec
		client.wscodec = codec
		event.complete = True  # TODO: can we modify it in this way?
		event.stop()
		self.fire(RE(client), client.server.channel)
		return response

	def select_subprotocol(self, subprotocols):
		return subprotocols[0]

	@handler('response_complete')
	def _websocket_connect(self, evt, value):
		client = evt.args[0]
		if client.socket in self._codecs:
			# FIXME: getpeername can return empty string?!
			self.fire(connect(client.socket, *client.socket.getpeername()), self._wschannel)

	@handler('disconnect')
	def _on_disconnect(self, socket):
		if socket in self._codecs:
			self.fire(disconnect(socket), self._wschannel)
			del self._codecs[socket]
