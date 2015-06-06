# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

import re
import gettext

from httoop import NOT_ACCEPTABLE


class GettextResource(object):

	_default_language = 'en-us'
	_fallback = True
	RE_LANG = re.compile('^([a-z][a-z])-([a-z][a-z])$')

	def content_language(self, client):
		localedir = client.domain.localedir
		textdomain = client.resource.textdomain(client)
		languages = client.request.headers.values('Accept-Language')

		translation = self.__get_translation(languages, textdomain, localedir)

		# Accept-Language is acceptable?
		if translation is None:
			raise NOT_ACCEPTABLE('The resource is not available in the requested Content-Language.')

		client.translation = translation.gettext
		return translation.language

	def __get_translation(self, languages, domain, localedir):
		for lang in languages:
			language = lang
			if '-' in language:
				# de-de → de_DE
				language = self.RE_LANG.sub(lambda pat: '%s_%s' % (pat.group(1), pat.group(2).upper()), language)
			if gettext.find(domain, localedir=localedir, languages=[language]):
				translation = gettext.translation(domain, localedir=localedir, languages=[language])
				translation.language = lang
				return translation
		if self._fallback:
			translation = gettext.translation(domain, localedir=localedir, languages=[self._default_language], fallback=self._fallback)
			if translation:
				translation.language = self._default_language
			return translation
