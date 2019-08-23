# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits import BaseComponent
from circuits.http.utils import httphandler

from httoop import PRECONDITION_REQUIRED


class PreconditionRequired(BaseComponent):

	@httphandler('request', priority=0.71)
	def _precondition_required(self, client):
		if not hasattr(client.resource, 'precondition_required'):
			return
		if not client.response.precondition_required(client):
			return
		if not any(x in client.request.headers for x in ('If-Unmodified-Since', 'If-None-Match', 'If-Modified-Since', 'If-Match')):
			# TODO: evaluate the request.method
			raise PRECONDITION_REQUIRED('Need a precondition like If-Unmodified-Since or If-None-Match.')
