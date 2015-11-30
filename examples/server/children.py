#!/usr/bin/env python2
"""Show parent-children relationship.

curl -i http://localhost:8090/forum
curl -i http://localhost:8090/forum/foo
curl -i http://localhost:8090/forum/foo/threads
curl -i http://localhost:8090/forum/foo/threads/bar
"""
import sys
sys.path.insert(0, '.')

from server import HTTPServer
from resource import BaseResource as Resource
from circuits import Debugger
from circuits.http.server.resource import method, Method


class ForumIndex(Resource):

	channel = '/forum'

	def init(self, **k):
		self += Forum()

	@method
	def GET(self, client):
		return u'Forum-index\n'
	GET.codec('text/plain', charset='UTF-8')


class Forum(Resource):

	def init(self, **k):
		self += ThreadIndex()

	channel = '{forum}'

	@method
	def GET(self, client):
		return u'Forum=%s\n' % (client.path_segments['forum'],)
	GET.codec('text/plain', charset='UTF-8')


class ThreadIndex(Resource):

	channel = 'threads'

	def init(self, **k):
		self += Thread()

	@method
	def GET(self, client):
		return u'Threads in forum %s\n' % (client.path_segments['forum'],)
	GET.codec('text/plain', charset='UTF-8')


class Thread(Resource):

	channel = '{thread}'

	@method
	def GET(self, client):
		return u'Forum: %s, Thread: %s\n' % (
			client.path_segments['forum'],
			client.path_segments['thread'],
		)
	GET.codec('text/plain', charset='UTF-8')


if __name__ == '__main__':
	server = HTTPServer()
	server.localhost += ForumIndex()
	server += Debugger(events=True)
	server.run()
