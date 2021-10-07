# -*- coding: utf-8 -*-

from httoop import ClientStateMachine
from httoop.semantic.request import ComposedRequest

from circuits.core import BaseComponent, handler
from circuits.http.events import response as ResponseEvent
from circuits.net.events import close, connect, write
from circuits.net.sockets import TCPClient
from circuits.six import reraise


class ClientStateMachine(ClientStateMachine):

	def on_message_started(self):
		super(ClientStateMachine, self).on_message_started()
		self.request = self.requests.pop(0)


class HTTPClient(BaseComponent):

	def __init__(self, channel):
		super(HTTPClient, self).__init__(channel=channel)
		self._buffers = {}
		self._socket_map = {}
		self._channel_sock = {}

	# @handler("close")
	# def _on_close(self):  # FIXME: socket argument missing
	# 	if self.socket.connected:
	# 		self.fire(close(), self.socket)

	@handler('connect', priority=1.0)
	def _on_connect(self, host=None, port=None, secure=None, certfile=None, keyfile=None, ca_certs=None):
		try:
			socket = self._socket_map[(host, port, secure)]
			if not socket.connected:
				raise KeyError
		except KeyError:
			socket = TCPClient(channel='%s_%d' % (self.channel, len(self._buffers))).register(self)
			self._buffers[socket] = {
				'parser': ClientStateMachine(),
				'socket': socket,
				'requests': [],
				'responses': [],
			}
			self._socket_map[(host, port, secure)] = socket
			self._channel_sock[socket.channel] = socket
		if not socket.connected:
			self.fire(connect(host, port, secure, certfile=certfile, keyfile=keyfile, ca_certs=ca_certs), socket)
		# event.stop()  # FIXME: self.call does conflict with this
		return socket

	@handler('request')
	def _on_request(self, client):
		if client.socket is None:
			host = client.request.uri.host
			port = client.request.uri.port
			secure = client.request.uri.scheme == u'https'
			result = yield self.call(connect(host, port, secure, certfile=client.ssl.cert, keyfile=client.ssl.key, ca_certs=[client.ssl.ca]))
			if result.errors:
				reraise(*result.value)
			client.socket = result.value
			if not client.socket.connected:
				yield self.wait("connected", client.socket.channel)

		try:
			state = self._buffers[client.socket]
		except KeyError:
			return  # server disconnected

		state['requests'].append(client)
		composer = ComposedRequest(client.request)
		composer.prepare()
		for data in composer:
			self.fire(write(data), client.socket)

		yield client
		# yield (yield self.wait("response"))

	@handler('read', channel='*')
	def _on_read(self, event, data):
		try:
			sock = [self._channel_sock.get(channel) for channel in event.channels]
			sock = [s for s in sock if s is not None][0]
		except IndexError:
			return  # socket does not belong to this component
		try:
			state = self._buffers[sock]
		except KeyError:
			return  # server disconnected
		parser = state['parser']
		parser.requests = [x.request for x in state['requests']]
		for response_ in parser.parse(data):
			try:
				client = state['requests'].pop(0)
			except IndexError:
				pass  # broken server send another message
			client.response = response_
			self.fire(ResponseEvent(client))

	@handler("response")
	def _on_response(self, client):
		if 'Connection' in client.response.headers and client.response.headers.element("Connection").close:  # TODO: ParsedResponse(response).close
			self.fire(close(), client.socket)
		return client
