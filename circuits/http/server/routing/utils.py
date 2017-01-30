# -*- coding: utf-8 -*-
# TODO: decide if this is a byte or unicode API

import re


def regexpath(path):
	try:
		route = ''.join(tokenize(path))
		return re.compile('^%s$' % route)
	except re.error as exc:
		raise ValueError('Invalid route: %s; %s' % (route, exc))


def tokenize(path):
	# special chars to indicate a natural split in the URL
	done_chars = ('/', ',', ';', '.', '#')
	reqs = {}

	regparts = []

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
				regparts.append(_append(current))
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
			regparts.append(_append(dict(type=var_type, name=current, var=reqs.get(current))))
			if char in done_chars:
				regparts.append(_append(char))
			done_on = var_type = current = ''
		else:
			current += char
	if collecting:
		regparts.append(_append(dict(type=var_type, name=current, var=reqs.get(current))))
	elif current:
		regparts.append(_append(current))
	return regparts


tokenize.defaults = {
	':': '[^/]+?',
	'.': '[^/.]+?',
	'*': '.+?'
}


def _append(part):
	if isinstance(part, dict):
		partmatch = part['var'] or tokenize.defaults[part['type']]
		regpart = '(?P<%s>%s)' % (part['name'], partmatch)
		if part['type'] == '.':
			return '(?:\.%s)??' % (regpart,)
		return regpart
	return re.escape(part)
