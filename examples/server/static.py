#!/usr/bin/env python2
"""Serve static content underneath of /etc/.

curl -i http://localhost:8090/passwd
curl -i http://localhost:8090/shadow

"""

import sys

sys.path.insert(0, '.')
from datetime import datetime

from circuits import BaseComponent, Debugger, handler
from circuits.http.server.resource import Domain, StaticResource
from circuits.tools import graph

from server import HTTPServer as _HTTPServer


class BaseResource(StaticResource):
	"""curl -i http://localhost:8090/passwd"""

	channel = '/*path'  # allows everything underneath of /etc/
	channel = '/:path'  # allows only files directly in /etc/

	def directory(self, client):
		return '/etc'


class HTTPServer(_HTTPServer):

	def __init__(self):
		super(HTTPServer, self).__init__()
		self.localhost += BaseResource()


if __name__ == '__main__':
	server = HTTPServer()
	server += Debugger(events=True)
	server.run()
