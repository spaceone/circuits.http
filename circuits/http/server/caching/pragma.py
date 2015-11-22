# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import sets_header, httphandler


class Pragma(BaseComponent):

	@httphandler('request', priority=0.4)
	@sets_header('Pragma', ifmethod=('GET', 'HEAD', 'OPTIONS'))
	def set_pragma_header(self, client):
		if hasattr(client.resource, 'pragma'):
			return client.resource.pragma(client)

