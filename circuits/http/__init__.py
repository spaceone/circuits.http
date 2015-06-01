# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

try:
	import httoop
except ImportError as exc:
	print('Missing httoop module. https://github.com/spaceone/httoop.\n')
	raise
else:
	del httoop
