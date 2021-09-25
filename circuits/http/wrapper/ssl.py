# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals


class SSL(object):

	def __init__(self, cert=None, key=None, ca=None):
		self.cert = cert
		self.key = key
		self.ca = ca
