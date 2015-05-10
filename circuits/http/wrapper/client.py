# -*- coding: utf-8 -*-
"""Client class which provides request, response and socket information"""

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits.http.wrapper.host import Host


class Client(object):

	server = None  # reference to the server
	socket = None  # reference to the connected client socket

	local = Host("127.0.0.1", 80)
	remote = Host("", 0)

	# TODO: how can we get rid of this? (belongs somewhere else)
	kwargs = None  # storage for e.g. translation instance
	domain = None
	resource = None
	method = None
	session = None
	user = None

	# TODO: move into server / statemachine
	done = False  # indicates that the response has been send to the socket
	handled = False  # indicated that the request has been handled

	def __init__(self, request, response, socket=None, server=None):
		"""
			:param request: the HTTP request
			:type request: :class:`httoop.Request`

			:param response: the http response
			:type response: :class:`httoop.Response`
		"""
		self.request = request
		self.response = response
		self.socket = socket
		self.server = server

		self.kwargs = {}

		if self.server is not None:
			self.local = Host(self.server.host, self.server.port)
			self.local.resolve()

		if self.socket is not None:
			self.remote = Host(*(
				self.socket.getpeername() or [self.socket.getsockname()[0], 0]
			))
			self.remote.resolve()  # TODO: resolve only when accessed?

#	def url(self, *path, **query):
#		# TODO: it could be nice to have a method to generate URL's
#		pass

	def __iter__(self):
		"""(request, response) = client"""
		return (self.request, self.response).__iter__()

	def __hash__(self):
		return hash(id(self))

	def __repr__(self):
		return '<Client(%r, request(%x), response(%x), id=%x)>' % (self.remote.ip, id(self.request), id(self.response), id(self))
