#!/usr/bin/env python2

import sys
sys.path.insert(0, '.')
import os

import mako
from mako.lookup import TemplateLookup

from server import HTTPServer
from resource import BaseResource as Resource
from circuits import Debugger
from circuits.http.server.resource import method

templates = TemplateLookup(
	directories=[os.path.join(os.path.dirname(__file__), "tpl")],
	module_directory="/tmp",
	output_encoding="utf-8"
)


class MakoTemplated(Resource):

	channel = '/'

	@method
	def GET(self, client):
		return {"message": "Hello World!"}

	GET.codec('application/json', 0.9)
	@GET.codec('text/html', 1.0, charset='utf-8')
	def _text_html(self, client):
		tpl = templates.get_template('index.html')
		return tpl.render(**client.data)


if __name__ == '__main__':
	server = HTTPServer()
	server.localhost += MakoTemplated()
	server += Debugger(events=True)
	server.run()
