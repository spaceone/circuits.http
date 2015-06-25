#!/usr/bin/env python2
# show parent-children relationship
# curl -i http://localhost:8090/forum/foo/threads/blub
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
		client.response.body = 'Forum-index'


class Forum(Resource):

	def init(self, **k):
		self += ThreadIndex()

	channel = '{forum}'

	@method
	def GET(self, client):
		client.response.body = 'Forum=%s' % (client.path_segments['forum'],)


class ThreadIndex(Resource):

	channel = 'threads'

	def init(self, **k):
		self += Thread()

	@method
	def GET(self, client):
		client.response.body = 'Threads in forum %s' % (client.path_segments['forum'],)


class Thread(Resource):

	channel = '{thread}'

	@method
	def GET(self, client):
		client.response.body = 'Forum: %s, Thread: %s' % (
			client.path_segments['forum'],
			client.path_segments['thread'],
		)

if __name__ == '__main__':
	server = HTTPServer()
	server.localhost += ForumIndex()
	server += Debugger(events=True)
	server.run()
