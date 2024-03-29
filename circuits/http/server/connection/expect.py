# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from httoop import CONTINUE, EXPECTATION_FAILED, Response

from circuits import BaseComponent
from circuits.http.utils import httphandler, if_header_set
from circuits.net.events import write


class Expect(BaseComponent):

	@httphandler('request', priority=.9)
	@if_header_set('Expect', ifmethod=('POST', 'PUT'))
	def expectatable(self, client):
		if hasattr(client.resource, 'expect'):
			return client.resource.expect(client)
		raise EXPECTATION_FAILED()


class ExpectContinue(object):

	def expect(self, client):
		for expect in client.request.headers.elements('Expect'):
			if expect.is_100_continue:
				if not self.expect_continue(client):
					raise EXPECTATION_FAILED()
				data = Response(status=CONTINUE().code)
				data = b'%s%s' % (data, data.headers)
				self.fire(write(data, client.socket), client.server.channel)
			else:
				raise EXPECTATION_FAILED('Unknown expect header: %r' % (expect,))

	def expect_continue(self, client):
		return True
