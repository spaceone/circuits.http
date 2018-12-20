"""
A WSGI server (gateway)

python wsgi_gateway.py -n --bind http://0.0.0.0:8090/
curl -i -X POST  http://localhost:8090/wsgi/foo/bar/baz
"""
from circuits.http.server.__main__ import HTTPServer
from circuits.http.server.resource import Resource, method, Domain
from circuits.http.server.wsgi import Gateway


def application(environ, start_response):
	status = '200 OK'
	variables = '\n'.join(' = '.join(map(lambda x: repr(x).lstrip('u').strip('"\''), x)) for x in sorted(environ.items()))
	output = b'Hello World!\n%s\n' % (variables,)

	response_headers = [('Content-type', 'text/plain'), ('Content-Length', str(len(output)))]
	start_response(status, response_headers)

	return [output]


class WSGI(Resource):

	path = '/wsgi/{path_info:.*}'

	def init(self, *args, **kwargs):
		self += Gateway(application, channel=self.channel)

	@method
	def GET(self, client):
		return


class Server(HTTPServer):

	logformat = '%(h)s %(l)s %(u)s %(t)s %(s)s "%(r)s" "%(H)s" %(b)s "%(f)s" "%(a)s"'

	def add_components(self):
		super(Server, self).add_components()
		root = Domain('localhost')
		root += HelloWorld(channel='hello-world')
		root += WSGI(channel='wsgi')
		self.domains += root


class HelloWorld(Resource):

	path = '/'

	@method
	def GET(self, client):
		return 'Content here!'
	GET.codec('text/plain')


Server.main()
