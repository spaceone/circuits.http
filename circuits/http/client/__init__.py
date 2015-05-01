# -*- coding: utf-8 -*-

from circuits.core import handler, BaseComponent, Event
from circuits.net.sockets import TCPClient
from circuits.net.events import close, connect, write

from httoop import ClientStateMachine
from httoop.client import ComposedRequest


class request(Event):
	success = True
	failure = True
#	complete = True


class response(Event):
	success = True
	failure = True
#	complete = True



class HTTPClient(BaseComponent):

	@property
	def connected(self):
		if hasattr(self, "socket"):
			return self.socket.connected

	socket = None

	def __init__(self, channel):
		super(HTTPClient, self).__init__(channel=channel)
		if self.socket is None:
			self.socket = TCPClient(channel=channel).register(self)
		self.state_machine = ClientStateMachine()

	@handler("close")
	def __on_close(self):
		if self.socket.connected:
			self.fire(close(), self.socket)

	@handler("connect", priority=1)
	def __on_connect(self, event, host=None, port=None, secure=None):
		if not self.socket.connected:
			self.fire(connect(host, port, secure), self.socket)

		event.stop()

	@handler("request")
	def __on_request(self, request):

		if not self.socket.connected:
			host = request.uri.host
			port = request.uri.port
			secure = request.uri.scheme == u'https'
			self.fire(connect(host, port, secure))
			yield self.wait("connected", self.socket.channel)

		composer = ComposedRequest(request)
		composer.prepare()
		for data in composer:
			self.fire(write(data), self.socket)

		yield request
		#yield (yield self.wait("response"))  # TODO: reimplement when we use client as argument

	@handler("read")
	def __on_read(self, data):
		for response_ in self.state_machine.parse(data):
			self.fire(response(response_))

	@handler("response")
	def __on_response(self, response):
		if response.headers.get("Connection") == "close":  # TODO: ParsedResponse(response).close
			self.fire(close(), self.socket)
		return response
