# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, handler
from circuits.six import text_type, string_types

import os
import sys
from io import IOBase
from datetime import datetime


class Logger(BaseComponent):

	_logformat = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
	_timeformat = '[%d/%b/%Y:%H:%M:%S]'

	def __init__(self, logfile=None, logger=None, logformat=_logformat, timeformat=_timeformat, **kwargs):
		super(Logger, self).__init__(**kwargs)

		if isinstance(logfile, string_types):
			self.file = open(os.path.abspath(os.path.expanduser(logfile)), 'a')
		elif isinstance(logfile, IOBase) or hasattr(logfile, 'write'):
			self.file = logfile
		else:
			self.file = sys.stdout

		self.logger = logger
		self._logformat = logformat
		self._timeformat = timeformat

	@handler('response.complete', priority=-0.1)
	def response(self, client):
		self.log(client)

	def log(self, client):
		request, response = client
		remote = client.remote

		host = request.headers.get('X-Forwarded-For', (remote.name or remote.ip))

		atoms = {
			'h': host,
			'l': '-',
			'u': getattr(getattr(client, 'user', None), 'username', None) or '-',
			't': self.formattime(),
			'r': '%s %s %s' % (request.method, request.uri.path, request.protocol),
			's': int(response.status),
			'b': response.headers.get('Content-Length', '') or '-',
			'f': request.headers.get('Referer', ''),
			'a': request.headers.get('User-Agent', ''),
			'H': request.headers.get('Host', ''),
		}
		for k, v in list(atoms.items()):
			if isinstance(v, text_type):
				v = v.encode('utf8')
			elif not isinstance(v, str):
				v = str(v)
			# Fortunately, repr(str) escapes unprintable chars, \n, \t, etc
			# and backslash for us. All we have to do is strip the quotes.
			v = repr(v)[1:-1]
			# Escape double-quote.
			atoms[k] = v.replace('"', '\\"')

		if self.logger is not None:
			self.logger.info(self._logformat % atoms)
		else:
			self.file.write(self._logformat % atoms)
			self.file.write('\n')
			self.file.flush()

	def formattime(self):
		return datetime.now().strftime(self._timeformat)
