circuits.http
=============

circuits.http is a asynchronous framework for building web and HTTP related applications such as HTTP servers, clients, proxies and caches.
It is based on two libraries  which allows very powerful and flexible API design:
* [circuits](https://github.com/circuits/circuits) which provides the asynchronous event system as well as socket handling
* [httoop](https://github.com/spaceone/httoop) as interface for handling of HTTP messages

The design of circuits.http is developped to build web applications in the [REST architectural style](http://www.ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm).

Features of the HTTP Server
===========================
* Standalone server
* [WSGI server](https://www.python.org/dev/peps/pep-0333/)
* Ressource oriented design with routing via
  * Domains / Hosts
  * Paths with wildcard and regex support
  * HTTP method
* [HTTPS connections](https://tools.ietf.org/html/rfc2818)
* Authentication via
  * [HTTP Basic](https://tools.ietf.org/html/rfc2617#section-2)
  * [HTTP Digest](https://tools.ietf.org/html/rfc2617#section-3)
  * HTTPS client/peer certificate
  * [SAML 2.0 service provider](https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf)
* Authorization to different Ressources via realm
* [Content-Negotiation](https://tools.ietf.org/html/rfc2295) via Accept, Accept-Language
* [MIME media type](http://www.iana.org/assignments/media-types/media-types.xhtml) decoding of request payload
  * [application/x-www-form-urlencoded](http://www.iana.org/assignments/media-types/application/x-www-form-urlencoded)
  * [multipart/form-data](http://www.iana.org/assignments/media-types/multipart/form-data)
  * [application/json](http://www.iana.org/assignments/media-types/application/json)
  * [application/xml](http://www.iana.org/assignments/media-types/application/xml) (requires [defusedxml](https://github.com/tiran/defusedxml))
  * support for custom extensibility
* validation of the request payload and error handling via HTTP 422 Unprocessable Entity
* encoding of the response payload for the following MIME media types
  * application/json
  * application/xml (requires [defusedxml](https://github.com/tiran/defusedxml))
  * text/plain
  * text/html (via [genshi](https://genshi.edgewall.org/))
* HTTP redirections via 3XX status codes
* HTTP Error handling via 4XX and 5XX status codes
* Internationalization support via gettext using HTTP Accept-Language and Content-Language
* [HTTP Range requests](https://tools.ietf.org/html/rfc7233)
* [HTTP Caching](https://tools.ietf.org/html/rfc7234) via Cache-Control, Expires, E-Tag, Last-Modified, Pragma and Vary
* [HTTP conditional requests](http://tools.ietf.org/html/7232) via If-Match, If-None-Match, If-Modified-Since, If-Unmodified-Since and If-Range
* HTTP Security mechanisms
  * [Content-Security-Policy](https://content-security-policy.com/)
  * [Strict-Transport-Security](https://tools.ietf.org/html/rfc6797)
  * [X-Frame-Options](https://tools.ietf.org/html/rfc7034)
  * X-XSS-Protection
  * X-Content-Type-Options
  * X-Permitted-Cross-Domain-Policies
* [Websocket protocol connections](https://tools.ietf.org/html/rfc6455)
* HTTP Expect 101 Continue per resource/request handling
* HTTP CONNECT method
* STARTTLS / [Upgrading to TLS encrypted connections](http://tools.ietf.org/html/2817)
* Request logging with configurable format
* Session handling via e.g. Cookies
* HTTP content encoding / compression via gzip, deflate
* HTTP chunked transfer encoding
* HTTP Trailers

Features of the HTTP Client
===========================
* Following redirections
* Sessions via Cookies with ability to define own Cookie-Policies

Planned Features
================
* [HTTP/2](https://http2.github.io/)
* support for Python 3.5 and greater
* Forwarded HTTP Extension [RFC 7239](https://tools.ietf.org/html/rfc7239)
* Prefer Header for HTTP [RFC 7240](https://tools.ietf.org/html/rfc7240)
* API for Web Linking ([RFC 5988](http://tools.ietf.org/html/5988))
* API for [Cross-Origin Resource Sharing](http://www.w3.org/TR/cors/)
* API for Content-Disposition ([RFC 6266](http://tools.ietf.org/html/6266))
* PoC for a HTTP Proxy implementation
* PoC for a HTTP Cache implementation
* automatic progress report via HTTP 202 Accepted
* SAML Identity Provider
* oAuth
* HTTP Age
* HTTP Warning
* [Public-Key-Pins](https://tools.ietf.org/html/rfc7469)

Examples
========
A simple HTTP server example with one resource which returns a plaintext document with the content "Hello World!" can be started with the following code:


Start a example server:
```sh
python examples/server/hello_world.py --bind http://0.0.0.0:8090/ --no-daemon
```

Request the resource either with firefox or with curl.
```sh
curl -i 'http://localhost:8090/'
firefox 'http://localhost:8090/'
```

```python
from circuits.http.server.__main__ import HTTPServer
from circuits.http.server.resource import Resource, method, Domain


class HelloWorld(Resource):

	path = '/'

	@method
	def GET(self, client):
		return 'Hello World!'
	GET.codec('text/plain')


class Server(HTTPServer):

	logformat = '%(h)s %(l)s %(u)s %(t)s %(s)s "%(r)s" "%(H)s" %(b)s "%(f)s" "%(a)s"'

	def add_components(self):
		super(Server, self).add_components()
		root = Domain('localhost')
		root += HelloWorld(channel='hello-world')
		self.domains += root


Server.main()
```

More examples:
* [Server examples](examples/server/)
* [Client examples](examples/client/)
* [A complete website using many features](https://github.com/spaceone/websites/)

Status
======
[![Build Status](https://travis-ci.org/spaceone/circuits.http.svg)](https://travis-ci.org/circuits/circuits)

[![codecov](https://codecov.io/gh/spaceone/circuits.http/branch/master/graph/badge.svg)](https://codecov.io/gh/circuits/circuits)
