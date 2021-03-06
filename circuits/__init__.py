# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
try:
	__import__('pkg_resources').declare_namespace(__name__)
except ImportError:
	from pkgutil import extend_path
	__path__ = extend_path(__path__, __name__)
	import os
	for _path in __path__:
		_path = os.path.join(_path, '__init__.py')
		if os.path.realpath(_path) != os.path.realpath(__file__) and os.path.exists(_path):
			with open(_path) as fd:
				exec(fd, globals())
		del _path
	del os, extend_path, fd
