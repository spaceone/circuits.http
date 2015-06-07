# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from functools import wraps
from inspect import getargspec

from circuits import handler as event_handler
from circuits.http.events import HTTPError

from httoop import HTTPStatusException


def sets_header(header, ifmethod=None):
	if not isinstance(ifmethod, (type(None), list, tuple)):
		ifmethod = (ifmethod,)
	def _decorator(func):
		@wraps(func)
		def _decorated(self, client, *args, **kwargs):
			if ifmethod and client.method not in ifmethod:
				return
			value = func(self, client, *args, **kwargs)
			if value is not None:
				client.response.headers[header] = value
		return _decorated
	return _decorator


def if_header_set(headers, ifmethod=None):
	if not isinstance(ifmethod, (type(None), list, tuple)):
		ifmethod = (ifmethod,)
	if not isinstance(headers, (list, tuple)):
		headers = (headers,)
	def _decorator(func):
		@wraps(func)
		def _decorated(self, client, *args, **kwargs):
			if ifmethod and client.method not in ifmethod:
				return
			if any(header in client.request.headers for header in headers):
				return func(self, client, *args, **kwargs)
		return _decorated
	return _decorator


def httperror(func):
	args = getargspec(func)[0]
	if args and args[0] == "self":
		del args[0]
	with_event = getattr(func, "event", bool(args and args[0] == "event"))
	@wraps(func)
	def _decorated(self, event, client, *args, **kwargs):
		try:
			args = tuple([client] + list(args))
			if with_event:
				args = tuple([event] + list(args))
			return func(self, *args, **kwargs)
		except HTTPStatusException as httperror_:
			event.stop()
			if client.events.request is not None:
				client.events.request.stop()
				client.events.request = None
			self.fire(HTTPError(client, httperror_), client.server.channel)
	return _decorated


def httphandler(*names, **kwargs):
	def _decorator(func):
		return event_handler(*names, **kwargs)(httperror(func))
	return _decorator


def allof(*conditions):
	"""All conditions of :attr:`conditions` have to be met"""
	def condition(client):
		return all(_condition(client) for _condition in conditions)
	return condition


def anyof(*conditions):
	"""Any condition of :attr:`conditions` have to be met"""
	def condition(client):
		return any(_condition(client) for _condition in conditions)
	return condition


def noneoff(*conditions):
	"""No condition of :attr:`conditions` must be met"""
	def condition(client):
		return all(not _condition(client) for _condition in conditions)
	return condition


def in_group(*groups):
	"""Returns True if the authenticated user is in any of the given groups"""
	def condition(client):
		return bool([group.name for group in client.user.groups] & groups)
	return condition


def is_user(*users):
	"""Returns True if the username is any of the given users"""
	def condition(client):
		return client.user.username in users
	return condition


def from_ip(*ips):
	"""Returns True if the request IP address is any of the given IP's"""
	def condition(client):
		return client.remote.ip in ips
	return condition


def from_hostname(*hostnames):
	"""Returns True if the request hostname is any of the given hostnames"""
	def condition(client):
		return client.remote.name in hostnames
	return condition


def is_https():
	"""Returns True if the connection is secured"""
	def condition(client):
		return client.request.uri.scheme == 'https'
	return condition
