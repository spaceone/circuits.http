from circuits import handler, BaseComponent, Debugger
from circuits.net.sockets import TCPServer

from circuits.http.server import HTTP
from circuits.http.server.resource import Domain
from circuits.http.server.routing import DomainRouter, Router
from circuits.http.server.log import Logger


class HTTPServer(BaseComponent):

	channel = 'http.server'

	def __init__(self):
		BaseComponent.__init__(self)
		http = HTTP(channel=self.channel)
		self += http
		self += Logger(channel=self.channel)
		http += TCPServer(('localhost', 8090), channel=self.channel)
		self += Router(channel=self.channel)
		self.domains = DomainRouter(channel=self.channel)
		self += self.domains

		self.localhost = Domain('localhost')
		self.domains += self.localhost


if __name__ == '__main__':
	server = HTTPServer()
	server += Debugger(events=True)
	server.run()
