# -*- coding: utf-8 -*-

import re


def regexpath(path):
	# special chars to indicate a natural split in the URL
	done_chars = ('/', ',', ';', '.', '#')
	reqs = {}

	regparts = []
	defaults = {
		':': '[^/]+?',
		'.': '[^/.]+?',
		'*': '.+?'
	}
	def append(part):
		if isinstance(part, dict):
			var = part['name']
			partmatch = reqs.get(var) or defaults[part['type']]
			regpart = '(?P<%s>%s)' % (var, partmatch)
			if part['type'] == '.':
				regparts.append('(?:\.%s)??' % regpart)
			else:
				regparts.append(regpart)
		else:
			regparts.append(re.escape(part))

	collecting = False
	current = ''
	done_on = ''
	var_type = ''
	just_started = False
	for char in path:
		if char in [':', '*', '{'] and not collecting:
			just_started = True
			collecting = True
			var_type = char
			if char == '{':
				done_on = '}'
				just_started = False
			if current:
				append(current)
				current = ''
		elif collecting and just_started:
			just_started = False
			if char == '(':
				done_on = ')'
			else:
				current = char
				done_on = done_chars + ('-',)
		elif collecting and char not in done_on:
			current += char
		elif collecting:
			collecting = False
			if var_type == '{':
				if current[0] == '.':
					var_type = '.'
					current = current[1:]
				else:
					var_type = ':'
				opts = current.split(':')
				if len(opts) > 1:
					current = opts[0]
					reqs[current] = opts[1]
			append(dict(type=var_type, name=current))
			if char in done_chars:
				append(char)
			done_on = var_type = current = ''
		else:
			current += char
	if collecting:
		append(dict(type=var_type, name=current))
	elif current:
		append(current)

	try:
		route = ''.join(regparts)
		return re.compile('^%s$' % route)
	except re.error as exc:
		raise ValueError('Invalid route: %s; %s' % (route, exc))
