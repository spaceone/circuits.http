#!/usr/bin/env python2
"""Authentication by parsing /etc/shadow.

curl -i http://root:bar@localhost:8090/
"""

import sys
sys.path.insert(0, '.')
import pwd
import re
from crypt import crypt

from server import HTTPServer
from resource import BaseResource as Resource
from circuits import Debugger, BaseComponent, handler
from circuits.http.server.resource import method
from circuits.http.events import authentication

from httoop import UNAUTHORIZED


class ShadowAuth(BaseComponent):

	@handler('authentication')
	def _on_shadow_auth(self, client):
		auth = client.request.headers.element('Authorization')
		if auth != 'Basic':
			print 'Only basic auth supported...', auth
			return
		username, password = auth.params['username'], auth.params['password']
		try:
			passwd = pwd.getpwnam(username).pw_passwd
		except KeyError:
			print 'Unknown user'
			return
		if passwd == 'x':
			print 'shadow password'
			with open('/etc/shadow') as shadow:
				rows = (line.strip().split(":") for line in shadow)
				hash_ = [row[1] for row in rows if row[0] == user]
				passwd = hash_ and _hash[0]
		salt = re.match(r'\$.*\$.*\$', passwd).group()
		if crypt(password, salt) == passwd:
			print 'authentication was successful'
			client.authenticated = True
			return
		print 'authentication failed'
		raise UNAUTHORIZED()

	@handler('routing', priority=2)
	def _on_request(self, client):
		client.authenticated = False
		yield self.wait(self.fire(authentication(client)).event)


class Protected(Resource):

	channel = '/'

	@method
	def GET(self, client):
		return {"message": "Top secret!"}
	GET.codec('application/json')
	GET.conditions(lambda client: client.authenticated)  # TODO: raise 401 Unauthorized


if __name__ == '__main__':
	server = HTTPServer()
	server.localhost += Protected()
	server += ShadowAuth(channel=server.channel)
	server += Debugger(events=True)
	server.run()
