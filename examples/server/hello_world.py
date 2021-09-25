from __future__ import absolute_import

from circuits.http.server.__main__ import HTTPServer
from circuits.http.server.resource import Domain, Resource, method


class HelloWorld(Resource):

	path = '/'

	@method
	def GET(self, client):
		return 'Hello World!'
	GET.codec('text/plain')


class Server(HTTPServer):

	logformat = '%(h)s %(l)s %(u)s %(t)s %(s)s "%(r)s" "%(H)s" %(b)s "%(f)s" "%(a)s"'

	def add_components(self):
		super(Server, self).add_components()
		root = Domain('localhost')
		root += HelloWorld(channel='hello-world')
		self.domains += root


Server.main()
