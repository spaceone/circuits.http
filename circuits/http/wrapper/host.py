# -*- coding: utf-8 -*-
"""Host class which contains IPv4, port and fqdn information"""

from __future__ import absolute_import
from __future__ import unicode_literals

import socket as _socket


class Host(object):
	"""An internet address containing IPv4 address, port and fqdn"""

	ip = '0.0.0.0'
	port = 80
	name = 'unknown.tld'

	def __init__(self, ip=None, port=None, name=None):
		self.ip = ip
		self.port = port
		if name is None:
			name = ip
		self.name = name

	def resolve(self):
		"""Resolve IP address and FQDN"""
		if not self.name or self.name == self.ip:
			self.name = _socket.getfqdn(self.ip)
		elif not self.ip:
			try:
				self.ip = _socket.gethostbyname(self.name)
			except _socket.gaierror:
				pass

	def __str__(self):
		return '%s:%d' % (self.ip, self.port)

	def __repr__(self):
		return 'Host(%r, %r, %r)' % (self.ip, self.port, self.name)
