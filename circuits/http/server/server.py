# -*- coding: utf-8 -*-
"""HTTP server"""

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.net.utils import is_ssl_handshake
from circuits.net.events import close
from circuits.http.wrapper import Client, Server
from circuits.http.events import HTTPError, request as Request

from httoop import ServerStateMachine, HTTPStatusException


class HTTP(BaseComponent):
	"""HTTP Server Protocol Component

		Parse incoming HTTP messages and send a response message.
	"""

	channel = 'http'

	def __init__(self, channel=channel):
		super(HTTP, self).__init__(channel=channel)
		self._buffers = {}
		self._client_ids = set()

	@handler("read")
	def _on_read(self, event, socket, data):
		"""parse data and fire request event"""

		server = Server(event.value.manager)

		if socket not in self._buffers:
			if not server.secure and is_ssl_handshake(data):
				# If we receive an SSL handshake at the start of a request
				# and we're not a secure server, then immediately close the
				# client connection since we can't respond to it anyway.
				self.fire(close(socket))
				return

			self._buffers[socket] = ServerStateMachine(server.scheme, server.host, server.port)

		http = self._buffers[socket]

		try:
			requests = tuple(http.parse(data))
		except HTTPStatusException as httperror:
			client = Client(http.request, http.response, socket, server)
			self._client_ids.add(id(client))
			self.fire(HTTPError(client, httperror))
			# TODO: wait for HTTPError event to be processed and close the connection
		else:
			for request, response in requests:
				client = Client(request, response, socket, server)
				self._client_ids.add(id(client))
				self.fire(Request(client))

	@handler("disconnect", "close")
	def _on_disconnect_or_close(self, socket=None):
		if not socket:
			return # close event when stopping the server
		self._remove_client(socket)

	def _remove_client(self, socket):
		if socket in self._buffers:
			del self._buffers[socket]
