# -*- coding: utf-8 -*-
"""circuits.http.server
"""

import os
import sys
from argparse import ArgumentParser
from socket import error as SocketError

from httoop import URI

from circuits import BaseComponent, Debugger
from circuits.app import Daemon, DropPrivileges
from circuits.core.helpers import FallBackExceptionHandler
from circuits.http import __name__ as name, __version__ as version
from circuits.http.server import HTTP
from circuits.http.server.log import Logger
from circuits.http.server.routing import DomainRouter
from circuits.net.sockets import TCP6Server, TCPServer, UDP6Server, UDPServer, UNIXServer


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

	logformat = None

	def __init__(self, *args, **kwargs):
		super(HTTPServer, self).__init__(*args, **kwargs)
		self.parser = ArgumentParser(name, description=__doc__, epilog='https://github.com/spaceone/circuits.http/')

	def run(self, args):
		self.add_arguments()
		self.parse_arguments(args)
		self.http = HTTP(channel=self.channel)
		self += self.http
		self.domains = DomainRouter(channel=self.channel)
		self += self.domains

		self.add_components()

		if not self.arguments.wsgi:
			super(HTTPServer, self).run()
		return self

	def add_arguments(self):
		add = self.parser.add_argument

		add('-b', '--bind', metavar='URI', action='append', default=[])
		add('-w', '--wsgi', action='store_true', help='Start as WSGI server')

		add(
			'-n', '--no-daemon', default=True, dest='daemonize', action='store_false',
			help="don't daemonize. The process will not fork into background")

		add(
			'-p', '--pid', default='/var/run/%s.pid' % (__name__,), dest='pidfile',
			help='The process id file which is required when running as daemon')

		add(
			'-u', '--user', default=None,
			help='the username or user id to run the process as. Only possible if run as root.')

		add(
			'-g', '--group', default=None,
			help='the groupname or group id to run the proccess as. Only possible if run as root.')

		add(
			'--umask', type=int,
			help='the umask this process should run as if dropping priviledges')

		add('-l', '--logfile', default=sys.stdout, dest='logfile', help='the logfile')

		add(
			'-d', '--debug', type=int, default=0, dest='loglevel',
			help='the loglevel as string or int (default: %(default)s)')

		add('-v', '--version', action='version', version=str(version))

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
		if any(arg is not None for arg in (self.arguments.user, self.arguments.group, self.arguments.umask)):
			self += DropPrivileges(self.arguments.user, self.arguments.group, self.arguments.umask, channel=self.channel)

	def add_logger(self):
		self += Logger(self.arguments.logfile, logformat=self.logformat, channel=self.channel)
		if self.arguments.loglevel:
			self += Debugger()
		else:
			self += FallBackExceptionHandler()

	def add_sockets(self):
		if not self.arguments.bind:
			if self.arguments.wsgi:
				return
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
			self.exit('Could not create socket for URI "%s": %s. Further socket options can be specified via the query string.' % (uri, exc,))
		except SocketError as exc:
			self.exit('Could not create socket %s: %s.' % (bind, exc))

	def exit(self, message, exitcode=1):
		sys.stderr.write(message)
		raise SystemExit(exitcode)

	@classmethod
	def main(cls, args=sys.argv[1:]):
		server = cls()
		server.run(args)
		return server


if __name__ == '__main__':
	HTTPServer.main()
