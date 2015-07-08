# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from circuits.http.server.resource.domain import Domain
from circuits.http.server.resource.resource import Resource
from circuits.http.server.resource.method import Method, method
from circuits.http.server.resource.static import StaticResource

__all__ = ('Domain', 'Resource', 'Method', 'method')
