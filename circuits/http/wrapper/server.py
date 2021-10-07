# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals


class Server(object):

	def __init__(self, server):
		self.socket = server

	@property
	def channel(self):
		return self.socket.channel

	@property
	def protocol(self):
		return (1, 1)

	# @property
	# def version(self):
	# 	return SERVER_VERSION

	@property
	def scheme(self):
		return u'https' if self.socket.secure else u'http'

	@property
	def host(self):
		return self.socket.host

	@property
	def port(self):
		return self.socket.port

	@property
	def secure(self):
		return self.socket.secure

	def __repr__(self):
		return '<Server(%s:%s)>' % (self.host, self.port)
