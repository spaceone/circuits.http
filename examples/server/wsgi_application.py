"""A WSGI application

Test with:
apt-get install libapache2-mod-wsgi

WSGIScriptAliasMatch /example(/.*) /var/www/wsgi_application.py$1
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

	path = '/'

	@method
	def GET(self, client):
		return 'Hello World!'
	GET.codec('text/plain')


server = WSGIServer.main('-d4')
application = Application(server)
application += server
