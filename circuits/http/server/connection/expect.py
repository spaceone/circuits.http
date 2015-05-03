# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.net.events import write
from circuits.http.utils import if_header_set

from httoop import EXPECTATION_FAILED, CONTINUE, Response


class Expect(BaseComponent):

	@handler('request', priority=.1)
	@if_header_set('Expect', ifmethod=('POST', 'PUT'))
	def expectatable(self, client):
		if hasattr(client.resource, 'expect'):
			return client.resource.expect(client)
		raise EXPECTATION_FAILED()


class ExpectContinue(object):

	def expect(self, client):
		for expect in client.request.headers.elements('Expect'):
			if expect.lower() == '100-continue':
				if not self.expect_continue(client):
					raise EXPECTATION_FAILED()
				data = Response(status=CONTINUE().code)
				data = b'%s%s' % (data, data.headers)
				self.fire(write(data, client.socket), client.server.channel)
			else:
				raise EXPECTATION_FAILED('Unknown expect header: %r' % (expect,))

	def expect_continue(self, client):
		return True
