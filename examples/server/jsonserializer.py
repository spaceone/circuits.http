#!/usr/bin/env python2

import sys
sys.path.insert(0, '.')

from server import HTTPServer
from resource import BaseResource as Resource
from circuits import Debugger
from circuits.http.server.resource import method


class JSONSerializer(Resource):

	channel = '/'

	@method
	def GET(self, client):
		return {"message": "Hello World!"}
	GET.codec('application/json', 1.1)


if __name__ == '__main__':
	server = HTTPServer()
	server.localhost += JSONSerializer()
	server += Debugger(events=True)
	server.run()
