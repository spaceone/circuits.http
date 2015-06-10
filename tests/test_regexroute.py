# -*- coding: utf-8 -*-
import re

from circuits.http.server.routing import regexpath


def test_string():
	assert regexpath('/foo/bar').pattern == r'^\/foo\/bar$'


def test_group_colon():
	assert regexpath('/:foo/:bar').pattern == r'^\/(?P<foo>[^/]+?)\/(?P<bar>[^/]+?)$'
	assert regexpath('/foo:bar').pattern == r'^\/foo(?P<bar>[^/]+?)$'


def test_group_brackets():
	assert regexpath('/foo/{bar}/baz').pattern == r'^\/foo\/(?P<bar>[^/]+?)\/baz$'
	assert regexpath('/foo/{bar:\d+}/baz').pattern == r'^\/foo\/(?P<bar>\d+)\/baz$'


def test_group_point():
	assert regexpath('/foo{.bar:jpe?g}').pattern == r'^\/foo(?:\.(?P<bar>jpe?g))??$'


def test_star():
	assert regexpath('/foo/*bar').pattern == r'^\/foo\/(?P<bar>.+?)$'
