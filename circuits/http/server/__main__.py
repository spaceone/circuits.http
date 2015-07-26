# -*- coding: utf-8 -*-
"""circuits.http.server
"""

import sys
from argparse import ArgumentParser

from httoop import URI

from circuits import BaseComponent, Debugger
from circuits.core.helpers import FallBackExceptionHandler
from circuits.net.sockets import TCPServer, UDPServer, UNIXServer

from circuits.http import __version__ as version, __name__ as name
from circuits.http.server import HTTP
from circuits.http.server.routing import DomainRouter, Router
from circuits.http.server.log import Logger


class HTTPServer(BaseComponent):

	channel = 'http.server'

	socket_types = {
		'http': TCPServer,
		'https': TCPServer,
		'tcp': TCPServer,
		'unix': UNIXServer,
		'udp': UDPServer,
	}

	def __init__(self, *args, **kwargs):
		super(HTTPServer, self).__init__(*args, **kwargs)
		self.parser = ArgumentParser(name, version=str(version), description=__doc__, epilog='https://github.com/spaceone/circuits.http/')

	def run(self, args):
		self.add_arguments()
		self.parse_arguments(args)
		self.http = HTTP(channel=self.channel)
		self += self.http
		self += Router(channel=self.channel)
		self.domains = DomainRouter(channel=self.channel)
		self += self.domains

		self.add_components()

		super(HTTPServer, self).run()

	def add_arguments(self):
		add = self.parser.add_argument

		add('-b', '--bind', metavar='URI', action='append', default=[])

		add('-n', '--no-daemon', default=True, dest='daemonize', action='store_false',
			help="don't daemonize. The process will not fork into background")

		add('-p', '--pid', default='/var/run/%s.pid' % (__name__,), dest='pidfile',
			help='The process id file which is required when running as daemon')

		add('-u', '--user', default=None,
			help='the username or user id to run the process as. Only possible if run as root.')

		add('-g', '--group', default=None,
			help='the groupname or group id to run the proccess as. Only possible if run as root.')

		add('-l', '--logfile', default=sys.stdout, dest='logfile', help='the logfile')

		add('-d', '--debug', type=int, default=0, dest='loglevel',
			help='the loglevel as string or int (default: %(default)s)')

	def parse_arguments(self, args):
		self.arguments = self.parser.parse_args(args)

	def add_components(self):
		self.add_daemonizing()
		self.add_drop_priviledges()
		self.add_logger()
		self.add_sockets()

	def add_daemonizing(self):
		pass

	def add_drop_priviledges(self):
		pass

	def add_logger(self):
		self += Logger(self.arguments.logfile, channel=self.channel)
		if self.arguments.loglevel:
			self += Debugger()
		else:
			self += FallBackExceptionHandler()

	def add_sockets(self):
		if not self.arguments.bind:
			import warnings
			warnings.warn('No socket to bind to. Use --bind.', RuntimeWarning)
		for bind in self.arguments.bind:
			self.add_socket(URI(bind))

	def add_socket(self, bind):
		# TODO: IPv6
		# FIXME: Unix-socket arguments
		SocketType = self.socket_types.get(bind.scheme, TCPServer)
		kwargs = dict(bind.query)
		if bind.scheme == 'https':
			kwargs['secure'] = True

		self.http += SocketType((bind.host, bind.port), channel=self.http.channel, **kwargs)

	@classmethod
	def main(cls, args=sys.argv[1:]):
		server = cls()
		server.run(args)


if __name__ == '__main__':
	HTTPServer.main()
