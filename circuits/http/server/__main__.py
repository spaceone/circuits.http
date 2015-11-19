# -*- coding: utf-8 -*-
"""circuits.http.server
"""

import sys
import os
from socket import error as SocketError
from argparse import ArgumentParser

from httoop import URI

from circuits import BaseComponent, Debugger
from circuits.core.helpers import FallBackExceptionHandler
from circuits.net.sockets import TCPServer, UDPServer, UNIXServer, TCP6Server, UDP6Server
from circuits.app import DropPrivileges, Daemon

from circuits.http import __version__ as version, __name__ as name
from circuits.http.server import HTTP
from circuits.http.server.routing import DomainRouter
from circuits.http.server.log import Logger


class HTTPServer(BaseComponent):

	channel = 'http.server'

	socket_types = {
		'http': TCPServer,
		'https': TCPServer,
		'tcp': TCPServer,
		'unix': UNIXServer,
		'udp': UDPServer,
		6: {
			'http': TCP6Server,
			'https': TCP6Server,
			'tcp': TCP6Server,
			'udp': UDP6Server,
		}
	}

	def __init__(self, *args, **kwargs):
		super(HTTPServer, self).__init__(*args, **kwargs)
		self.parser = ArgumentParser(name, version=str(version), description=__doc__, epilog='https://github.com/spaceone/circuits.http/')

	def run(self, args):
		self.add_arguments()
		self.parse_arguments(args)
		self.http = HTTP(channel=self.channel)
		self += self.http
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

		add('--umask', type=int,
			help='the umask this process should run as if dropping priviledges')

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
		if self.arguments.daemonize:
			self += Daemon(self.arguments.pidfile, os.getcwd())

	def add_drop_priviledges(self):
		self += DropPrivileges(self.arguments.user, self.arguments.group, self.arguments.umask, channel=self.channel)

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

	def add_socket(self, uri):
		SocketType = self.socket_types.get(uri.scheme, TCPServer)
		bind = (uri.host, uri.port)

		# IPv6
		if uri.host.startswith('[') and uri.host.endswith(']'):
			SocketType = self.socket_types[6].get(uri.scheme, TCP6Server)
			bind = (uri.host[1:-1], uri.port)

		# UNIX sockets
		if uri.scheme == 'unix':
			bind = uri.path

		# HTTPS
		kwargs = dict(uri.query)
		if uri.scheme == 'https':
			kwargs['secure'] = True

		try:
			self.http += SocketType(bind, channel=self.http.channel, **kwargs)
		except RuntimeError as exc:
			self.exit('Could not create socket for URI "%s": %s. Further socket options can be specified via the query string.' % (uri.uri, exc,))
		except SocketError as exc:
			self.exit('Could not create socket %s: %s.' % (bind, exc))

	def exit(self, message, exitcode=1):
		sys.stderr.write(message)
		raise SystemExit(exitcode)

	@classmethod
	def main(cls, args=sys.argv[1:]):
		server = cls()
		server.run(args)


if __name__ == '__main__':
	HTTPServer.main()
