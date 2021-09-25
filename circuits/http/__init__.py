# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

__version__ = (0, 0)

try:
	import httoop
except ImportError as exc:
	print('Missing httoop module. https://github.com/spaceone/httoop.\n')
	raise
else:
	del httoop
