# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent, Event, handler
from circuits.http.server.routing.router import Router
from circuits.http.server.routing.utils import regexpath
from circuits.http.server.resource import Resource, Domain


class RegexPathRouter(Router):

	def __init__(self, channel):
		BaseComponent.__init__(self, channel=channel)
		self.routes = set()
		# TODO: fire routes.create on sub-resource unregistered

	@handler('started', channel='*')
	def _on_started(self, manager):
		self.fire(Event.create(b'routes.create'))

	@handler('routes.create')
	def _on_register_routes(self):
		routes = set()
		for resource in self._all_childs(self.parent.children):
			path = self._build_tree_path(resource)
			routes.update(resource.routes)
			routes.add((resource, regexpath(path)))
		self.routes = routes

	@handler('routing')
	def _find_resource(self, client):
		path = client.request.uri.path
		for resource, path_segments in self.match(path):
			if resource.identify(client, path_segments):
				client.resource = resource
				client.path_segments = path_segments

	def match(self, path):
		for resource, pattern in self.routes:
			#defaults = pattern.groupindex.keys()
			result = pattern.match(path)
			if result:
				yield resource, result.groupdict()

	def _all_childs(self, childrens):
		for children in childrens:
			if children.children:
				for c in self._all_childs(children.children):
					yield c
			yield children

	def _build_tree_path(self, resource):
		parent = resource.parent
		if isinstance(parent, Domain):
			return resource.path
		path = []
		while isinstance(parent, Resource):
			if parent is parent.parent:
				break
			path.insert(0, parent.path.lstrip('/'))
			parent = parent.parent
		path.insert(0, '')
		path.append(resource.path.lstrip('/'))
		return b'/'.join(path)
