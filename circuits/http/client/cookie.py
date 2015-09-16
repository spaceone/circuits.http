# -*- coding: utf-8 -*-

from time import time

from circuits.core import handler, BaseComponent


class Cookie(object):

	@property
	def persistent(self):
		return self.max_age is not None or self.expired is not None

	def __init__(self, cookie_name, cookie_value, host, **kwargs):
		self.cookie_name = cookie_name
		self.cookie_value = cookie_value
		self.host = host
		self.domain = kwargs.get('domain')
		self.path = kwargs.get('path')
		self.max_age = kwargs.get('max_age') and int(kwargs['max_age'])
		self.expires = kwargs.get('expires') and int(kwargs['expires'])
		self.secure = kwargs.get('secure')
		self.httponly = kwargs.get('httponly')
		self.creation_time = kwargs.get('creation_time')
		self.last_access_time = kwargs.get('last_access_time')

	def expired(self):
		if not self.persistent:
			return False
		if self.max_age and time() >= self.max_age + self.creation_time:
			return True
		if self.expired and time() >= self.expired:
			return True
		return False


class CookieStorage(BaseComponent):

	def init(self, *args, **kwargs):
		self.cookies = set()

	@handler('response', priority=1.1)
	def _on_response(self, client):
		for cookie in client.response.headers.elements('Set-Cookie'):
			now = time()
			cookie = Cookie(cookie.cookie_name, cookie.cookie_value, client.request.uri.host,
				domain=cookie.domain,
				path=cookie.path,
				max_age=cookie.max_age,
				expires=cookie.expires,
				secure=cookie.secure,
				httponly=cookie.httponly,
				creation_time=now,
				last_access_time=now,
			)
			self.add_cookie(client, cookie)

	def add_cookie(self, client, cookie):
		cookie_ = self.get_cookie(cookie)
		if cookie_ is not None:
			self.delete_cookie(cookie_)
			cookie.creation_time = cookie_.creation_time
		if not cookie.expired():
			self.cookies.add(cookie)

	def get_cookie(self, cookie):
		for cookie_ in self.cookies.copy():
			if cookie_.cookie_name != cookie.cookie_name:
				continue
			if not cookie.domain and cookie_.host != cookie.host:
				continue
			if cookie.domain and cookie_.domain != cookie.domain:
				continue
			if cookie.path and cookie_.path != cookie.path:
				continue
			return cookie_

	def delete_cookie(self, cookie):
		try:
			self.cookies.remove(cookie)
		except KeyError:
			pass

	@handler('request', priority=1.1)
	def _on_request(self, client):
		cookies = self.cookies
		if not cookies:
			return
		is_secure = self.is_secure(client)
		for cookie in cookies.copy():
			if not self.cookie_matches(client, cookie, is_secure):
				continue
			# TODO: use httoop for this
			if 'Cookie' not in client.request.headers:
				client.request.headers.append('Cookie', u'%s=%s' % (cookie.cookie_name, cookie.cookie_value))
			else:
				dict.__setitem__(client.request.headers, 'Cookie', u'%s\r\nCookie: %s=%s' % (client.request.headers['Cookie'], cookie.cookie_name, cookie.cookie_value))

	def cookie_matches(self, client, cookie, is_secure):
		if cookie.secure and not is_secure:
			return False
		if not cookie.domain and not self.host_matches(client.request.uri.host, cookie.host):
			return False
		if cookie.domain and not self.domain_matches(client.request.uri.host, cookie.domain):
			return False
		if cookie.path and not self.path_matches(client.request.uri.path, cookie.path):
			return False
		if cookie.expired():
			self.delete_cookie(cookie)
			return False
		return True

	def is_secure(self, client):
		return client.request.uri.scheme == u'https'

	def path_matches(self, path, cookie_path):
		return path.startswith(cookie_path)

	def host_matches(self, host, cookie_host):
		return host == cookie_host

	def domain_matches(self, domain, cookie_domain):
		if domain == cookie_domain:
			return True
		# FIXME: this currently allows ".com"
		if cookie_domain.startswith('.') and domain.endswith(cookie_domain):
			return True
		# TODO: substring
