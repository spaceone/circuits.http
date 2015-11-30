#!/usr/bin/env python2
"""HTTP TRACE method request.

curl -i http://localhost:8090/ -X TRACE
"""

import sys
sys.path.insert(0, '.')

from server import HTTPServer
from resource import BaseResource as Resource
from circuits import Debugger
from circuits.http.server.resource import method


class Trace(Resource):

	channel = '/'

	@method
	def TRACE(self, client):
		return client.request
	TRACE.codec('message/http')


if __name__ == '__main__':
	server = HTTPServer()
	server.localhost += Trace()
	server += Debugger(events=True)
	server.run()
