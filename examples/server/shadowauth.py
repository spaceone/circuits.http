#!/usr/bin/env python2

import sys
sys.path.insert(0, '.')
import pwd
import re
from crypt import crypt

from server import HTTPServer
from resource import BaseResource as Resource
from circuits import Debugger, BaseComponent, handler
from circuits.http.server.resource import method

from httoop import UNAUTHORIZED


class ShadowAuth(BaseComponent):

	@handler('authentication')
	def _on_shadow_auth(self, client):
		auth = client.request.headers.element('Authentication')
		if auth != 'basic':
			return
		username, password = auth.username, auth.password
		try:
			passwd = pwd.getpwnam(username).pw_passwd
		except KeyError:
			return
		if passwd == 'x':
			with open('/etc/shadow') as shadow:
				rows = (line.strip().split(":") for line in shadow)
				hash_ = [row[1] for row in rows if row[0] == user]
				passwd = hash_ and _hash[0]
		salt = re.match(r'\$.*\$.*\$', passwd).group()
		if crypt(password, salt) == passwd:
			client.authenticated = True
			return
		raise UNAUTHORIZED()


class Protected(Resource):

	channel = '/'

	@method
	def GET(self, client):
		return {"message": "Top secret!"}
	GET.codec('application/json')
	GET.conditions(lambda client: client.authenticated)


if __name__ == '__main__':
	server = HTTPServer()
	server.localhost += Protected()
	server += ShadowAuth(channel=server.channel)
	server += Debugger(events=True)
	server.run()
