# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits.http.events import HTTPError
from httoop import HTTPStatusException


def sets_header(header, ifmethod=None):
	def _decorator(func):
		def _decorated(self, client, *args, **kwargs):
			if ifmethod and client.method not in ifmethod:
				return
			value = func(self, client, *args, **kwargs)
			if value is not None:
				client.response.headers[header] = value
		return _decorated
	return _decorator


def if_header_set(header, ifmethod=None):
	def _decorator(func):
		def _decorated(self, client, *args, **kwargs):
			if ifmethod and client.method not in ifmethod:
				return
			if header in client.request.headers:
				return func(self, client, *args, **kwargs)
		return _decorated
	return _decorator


def httperror(func):
	def _decorated(self, event, client, *args, **kwargs):
		try:
			return func(self, client, *args, **kwargs)
		except HTTPStatusException as httperror:
			event.stop()
			self.fire(HTTPError(client, httperror))
	return _decorated


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
