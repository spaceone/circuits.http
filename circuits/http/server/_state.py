# -*- coding: utf-8 -*-
"""HTTP server"""

from __future__ import absolute_import, unicode_literals

from httoop.server import ServerStateMachine

from circuits.http.wrapper import Client


class StateMachine(ServerStateMachine):

	def __init__(self, http, client, server, *args):
		self.__http = http
		self.__client = client
		self.__server = server
		super(StateMachine, self).__init__(*args)

	def on_headers_complete(self):
		super(StateMachine, self).on_headers_complete()
		self.__http.on_headers_complete(self.client)

	def on_message_complete(self):
		super(StateMachine, self).on_message_complete()
		return self.client

	def on_message_started(self):
		super(StateMachine, self).on_message_started()
		self.client = Client(self.request, self.response, self.__client, self.__server)


class State(object):

	__slots__ = ('http', 'parser', 'requests', 'responses', 'response_started', 'composed', 'timeout', 'tunnel')

	def __init__(self, http, client, server):
		self.parser = StateMachine(http, client, server, server.scheme, server.host, server.port)
		self.requests = []
		self.responses = set()
		self.response_started = set()
		self.composed = {}
		self.timeout = None
		self.tunnel = None
