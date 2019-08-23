# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

import re
import gettext

from circuits.http.utils import httphandler


class GettextResource(object):

	default_languages = [u'en-US']
	fallback = True
	RE_LANG = re.compile(u'^([a-z][a-z])-([a-z][a-z])$', re.I)

	@httphandler('request', priority=1.0)
	def _set_null_translation(self, client):
		client.translation = gettext.NullTranslations()

	def content_language(self, client):
		localedir = client.domain.localedir
		textdomain = client.resource.textdomain(client)
		languages = client.request.headers.values('Accept-Language')

		translation = self.__get_translation(languages, textdomain, localedir)
		if not translation:
			return

		client.translation = translation
		translation._info.setdefault('language', '')
		return translation._info['language'].replace('_', '-')

	def __get_translation(self, languages, domain, localedir):
		for language in languages:
			locale = language
			if '-' in language:
				# de-de → de_DE
				locale = self.RE_LANG.sub(lambda pat: '%s_%s' % (pat.group(1), pat.group(2).upper()), language)
			try:
				translation = gettext.translation(domain, localedir=localedir, languages=[locale])
			except IOError:
				continue
			translation._info.setdefault('language', locale)
			return translation
		if self.fallback:
			return gettext.translation(domain, localedir=localedir, languages=self.default_languages, fallback=self.fallback)
