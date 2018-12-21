"""A WSGI application

Test with:
apt-get install libapache2-mod-wsgi

WSGIScriptAlias /example /var/www/wsgi_application.py
curl -i http://localhost/example/
"""

from circuits.http.server.resource import Resource, method, Domain
from circuits.http.server.wsgi import Application, WSGIServer


class Server(WSGIServer):

	logformat = '%(h)s %(l)s %(u)s %(t)s %(s)s "%(r)s" "%(H)s" %(b)s "%(f)s" "%(a)s"'

	def add_components(self):
		super(Server, self).add_components()
		root = Domain('localhost')
		root += HelloWorld(channel='hello-world')
		self.domains += root


class HelloWorld(Resource):

	path = '/{path:.*}'

	@method
	def GET(self, client):
		if 'exception' in client.path_segments:
			raise ValueError('Hello World!')
		return 'Hello World!'
	GET.codec('text/plain')


application = Application(Server, '-d4')
