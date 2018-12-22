# -*- coding: utf-8 -*-

import sys
import os
import traceback
from argparse import ArgumentParser

from httoop import Request
from httoop.header import Authorization

from circuits import handler, Debugger
from circuits.http.client import HTTPClient
from circuits.http.events import request as RequestEvent
from circuits.http.wrapper import Client


class Curl(HTTPClient):
	"""A curl CLI equivalent (not libcurl)"""

	def __init__(self):
		self.parse_arguments()
		self.response_received = 0
		a = self.arguments

		if a.manual:
			os.execve('/usr/bin/man', ['5', 'curl'], os.environ)

		# connection + socket
		#capath = a.capath  # verify_peer
		#cacert = a.cacert
		#verify_server_cert = a.cert_status

		#cert = a.cert  # client certificate
		#certtype = a.cert_type

		super(Curl, self).__init__(channel='curl')
		if a.debug:
			self += Debugger()

		for url in a.url:
			self.build_request(url)

	def build_request(self, url):
		a = self.arguments
		request = Request(a.request, url)

		# HTTP protocol
		if a.http1_0:
			request.protocol = (1, 0)
		if a.http2:
			self.parser.error('HTTP/2 not supported')

		# HTTP Header
		for header in a.header:
			request.headers.parse(header)

		if a.user_agent:
			request.headers['User-Agent'] = a.user_agent
		if a.referer:
			request.headers['Referer'] = a.referer

		if a.cookie:
			if '=' not in a.cookie:
				with open(a.cookie) as fd:
					a.cookie = fd.read()
			request.headers['Cookie'] = a.cookie

		# HTTP authentication
		username, password = None, None
		if a.user:
			username, _, password = a.user.partition(':')
		if request.uri.username:
			username = request.uri.username
		if request.uri.password:
			password = request.uri.password

		if a.anyauth:
			a.basic = a.anyauth
			a.digest = a.anyauth
			a.ntlm = a.anyauth
			a.negotiate = a.anyauth
		if a.basic:
			basic = Authorization('Basic', {
				'username': username,
				'password': password,
			})
			request.headers['Authorization'] = bytes(basic)
		elif a.digest:
			pass
		elif a.ntlm:
			pass
		elif a.negotiate:
			pass

		# Request Body
		if a.upload_file:
			request.body = a.upload_file
		else:
			data = a.data or a.data_binary or a.data_urlencode
			if data:
				content_type = 'application/x-www-form-urlencoded'
			elif a.form or a.form_string:
				data = a.form or a.form_string
				content_type = 'multipart/form-data'

			if data:
				request.headers.setdefault('Content-Type', content_type)
				request.body.mimetype = request.headers.element('Content-Type').mimetype
				request.body = data

		request.method = 'HEAD' if a.head else (a.request or 'POST' if not a.get else 'GET')

		client = Client(request, None)
		self.fire(RequestEvent(client))

	@handler('exception')
	def _on_excpetion(self, *args, **kwargs):
		print ''.join(traceback.format_exception_only(args[0], args[1]) + args[2])
		self.stop(1)

	@handler('request_success')
	def request(self, evt, client):
		if self.arguments.verbose:
			self.arguments.stderr.write(bytes(client.request))
			self.arguments.stderr.write(bytes(client.request.headers))

	@handler('response_success')
	def response(self, evt, client):
		self.response_received += 1
		request, response = client
		if self.arguments.include or self.arguments.head:
			self.arguments.output.write(bytes(response))
			self.arguments.output.write(bytes(response.headers))
		if self.arguments.dump_header:
			self.arguments.dump_header.write(bytes(response))
			self.arguments.dump_header.write(bytes(response.headers))

		if self.arguments.write_out:
			self.write_output_format(response)
		elif not self.arguments.silent:
			self.arguments.output.write(bytes(response.body))

		follow_redirects = self.arguments.location
		if response.status.redirection and follow_redirects:
			pass

		if self.response_received >= len(self.arguments.url):
			self.stop()

	def write_output_format(self, response):
		write_out = self.arguments.write_out
		if write_out == '@-':
			write_out = sys.stdin.read()
		elif write_out.startswith('@'):
			with open(write_out[1:]) as fd:
				write_out = fd.read()

		import re
		write_out = re.sub('(^|[^%])%{([^}]+)}', r'\1%(\2)s', write_out).replace('%%', '%(percent)s')  # FIXME: incomplete

		class FormatDict(dict):  # time consuming things can be inserted manually in __get...__
			pass
		write_out = write_out % FormatDict({
			'percent': '%',
			'content_type': response.headers.get('Content-Type'),
			'http_code': response.status.code,
			'local_ip': self.socket.host,
			'local_port': self.socket.port,
			# TODO: implement the rest
		})

		self.arguments.output.write(write_out)

	@handler('error')
	def error(self, error, *args, **kwargs):
		if self.arguments.show_error:
			self.arguments.stderr.write(repr(error))

#	@handler('read')
#	def read(self, data):
#		print 'read', len(data)

#	@handler('write')
#	def write(self, data):
#		print 'write', repr(data)

	@handler('disconnected')
	def close(self, *sock):
		self.stop()

	def parse_arguments(self):
		self.parser = ArgumentParser(prog='curl', usage='%(prog)s [options...] <url>', description='Options: (H) means HTTP/HTTPS only, (F) means FTP only')

		unsupported = self.unsupported

		p = self.parser
		o = p.add_argument_group('Output').add_argument
		c = p.add_argument_group('Connection').add_argument
		h = p.add_argument_group('HTTP[S]').add_argument
		s = p.add_argument_group('SSL').add_argument
		so = p.add_argument_group('SOCKS').add_argument
		f = p.add_argument_group('[S]FTP').add_argument
		m = p.add_argument_group('Mail (SMTP, IMAP, POP3)').add_argument
		a = p.add_argument_group('Rest').add_argument  # TODO: category for these general things

		p.add_argument('url', metavar='<url>', nargs='*')

		o('--debug', action='store_true', help='Enabled the debugger')
		o('-#', '--progress-bar', help='Display transfer progress as a progress bar', action='store_true')
		o('-I', '--head', help='Show document info only', action='store_true')
		o('-M', '--manual', help='Display the full manual', action='store_true')
		o('-o', '--output', metavar='FILE', help='Write to FILE instead of stdout', default=sys.stdout, type=file)
		o('-S', '--show-error', help='Show error. With -s, make curl show errors when they occur', action='store_true')
		o('-s', '--silent', help='Silent mode (don\'t output anything)', action='store_true')
		o('--stderr', metavar='FILE', help='Where to redirect stderr (use "-" for stdout)', type=file, default=sys.stderr)
		o('-v', '--verbose', help='Make the operation more talkative', action='store_true')
		o('-w', '--write-out', metavar='FORMAT', help='Use output FORMAT after completion')
		o('-D', '--dump-header', metavar='FILE', help='Write the headers to FILE', type=file)

		a('-K', '--config', metavar='FILE', help='Read config from FILE', type=unsupported('config'))
		a('--create-dirs', help='Create necessary local directory hierarchy', action='store_true')
		a('--compressed', help='Request compressed response (using deflate or gzip)', action='store_true')
		a('-C', '--continue-at', metavar='OFFSET', help='Resumed transfer OFFSET')
		a('--crlf', help='Convert LF to CRLF in upload', action='store_true')
		a('--crlfile', metavar='FILE', help='Get a CRL list in PEM format from the given file')
		a('--delegation', metavar='LEVEL', help='GSS-API delegation permission')
		a('-g', '--globoff', help='Disable URL sequences and ranges using {} and []', action='store_true')
		a('--hostpubmd5', metavar='MD5', help='Hex-encoded MD5 string of the host public key. (SSH)')
		a('--libcurl', metavar='FILE', help='Dump libcurl equivalent code of this command line', type=unsupported())
		a('--limit-rate', metavar='RATE', help='Limit transfer speed to RATE')
		a('--metalink', help='Process given URLs as metalink XML file', action='store_true')
		a('-n', '--netrc', help='Must read .netrc for user name and password', action='store_true')
		a('--netrc-optional', help='Use either .netrc or URL; overrides -n', action='store_true')
		a('--netrc-file', metavar='FILE', help='Specify FILE for netrc')
		a('-:', '--next', help='Allows the following URL to use a separate set of options', action='store_true')
		a('-N', '--no-buffer', help='Disable buffering of the output stream', action='store_true')
		a('--path-as-is', help='Do not squash .. sequences in URL path', action='store_true')
		a('--proto', metavar='PROTOCOLS', help='Enable/disable PROTOCOLS')
		a('--proto-redir', metavar='PROTOCOLS', help='Enable/disable PROTOCOLS on redirect')
		a('--pubkey', metavar='KEY', help='Public key file name (SSH)')
		a('-r', '--range', metavar='RANGE', help='Retrieve only the bytes within RANGE')
		a('-O', '--remote-name', help='Write output to a file named as the remote file')
		a('--remote-name-all', help='Use the remote file name for all URLs')
		a('-R', '--remote-time', help='Set the remote file\'s time on the local output')
		a('--sasl-ir', help='Enable initial response in SASL authentication', action='store_true')
		a('-t', '--telnet-option', metavar='OPT=VAL', help='Set telnet option')
		a('-z', '--time-cond', metavar='TIME', help='Transfer based on a time condition')
		a('--trace', metavar='FILE', help='Write a debug trace to FILE')
		a('--trace-ascii', metavar='FILE', help='Like --trace, but without hex output')
		a('--trace-time', help='Add time stamps to trace/verbose output', action='store_true')
		a('-T', '--upload-file', metavar='FILE', help='Transfer FILE to destination', type=file)
		a('--url', metavar='URL', help='URL to work with', action='append')
		a('-B', '--use-ascii', help='Use ASCII/text transfer', action='store_true')
		a('-u', '--user', metavar='USER[:PASSWORD]', help='Server user and password')
		a('-V', '--version', help='Show version number and quit', action='store_true')
		a('--xattr', help='Store metadata in extended file attributes', action='store_true')
		a('-q', help='Disable .curlrc (must be first parameter)', action='store_true')

		# Connection
		c('--interface', metavar='INTERFACE', help='Use network INTERFACE (or address)')
		c('-4', '--ipv4', help='Resolve name to IPv4 address', action='store_true')
		c('-6', '--ipv6', help='Resolve name to IPv6 address', action='store_true')
		c('--unix-socket', metavar='FILE', help='Connect through this Unix domain socket')
		c('--keepalive-time', metavar='SECONDS', help='Wait SECONDS between keepalive probes')
		c('--connect-timeout', metavar='SECONDS', help='Maximum time allowed for connection')
		c('-m', '--max-time', metavar='SECONDS', help='Maximum time allowed for the transfer')
		c('--no-keepalive', help='Disable keepalive use on the connection', action='store_true')
		c('--local-port', metavar='RANGE', help='Force use of RANGE for local port numbers')
		c('--resolve', metavar='HOST:PORT:ADDRESS', help='Force resolve of HOST:PORT to ADDRESS', action='append')
		c('--retry', metavar='NUM', help='Retry request NUM times if transient problems occur')
		c('--retry-delay', metavar='SECONDS', help='Wait SECONDS between retries')
		c('--retry-max-time', metavar='SECONDS', help='Retry only within this period')
		c('--dns-servers', help='DNS server addrs to use: 1.1.1.1;2.2.2.2')
		c('--dns-interface', help='Interface to use for DNS requests')
		c('--dns-ipv4-addr', help='IPv4 address to use for DNS requests, dot notation')
		c('--dns-ipv6-addr', help='IPv6 address to use for DNS requests, dot notation')
		c('--tcp-nodelay', help='Use the TCP_NODELAY option', action='store_true')
		c('-Y', '--speed-limit', metavar='RATE', help='Stop transfers below RATE for \'speed-time\' secs')
		c('-y', '--speed-time', metavar='SECONDS', help='Trigger \'speed-limit\' abort after SECONDS (default: 30)')

		# SOCKS
		so('--socks4', metavar='HOST[:PORT]', help='SOCKS4 proxy on given host + port')
		so('--socks4a', metavar='HOST[:PORT]', help='SOCKS4a proxy on given host + port')
		so('--socks5', metavar='HOST[:PORT]', help='SOCKS5 proxy on given host + port')
		so('--socks5-hostname', metavar='HOST[:PORT]', help='SOCKS5 proxy, pass host name to proxy')
		so('--socks5-gssapi-service', metavar='NAME', help='SOCKS5 proxy service name for GSS-API')
		so('--socks5-gssapi-nec', help='Compatibility with NEC SOCKS5 server', action='store_true')

		# HTTP/HTTPS
		h('-X', '--request', metavar='COMMAND', help='Specify request command to use', default='GET')

		h('-H', '--header', action='append', metavar='LINE', help='Pass custom header LINE to server (H)', default=[])
		h('-A', '--user-agent', metavar='STRING', help='Send User-Agent STRING to server (H)')
		h('-e', '--referer', help='Referer URL (H)')
		h('-b', '--cookie', metavar='STRING/FILE', help='Read cookies from STRING/FILE (H)')
		h('-c', '--cookie-jar', metavar='FILE', help='Write cookies to FILE after operation (H)')

		h('-0', '--http1.0', dest='http1_0', help='Use HTTP 1.0 (H)', action='store_true')
		h('--http1.1', dest='http1_1', help='Use HTTP 1.1 (H)', action='store_true', default=True)
		h('--http2', help='Use HTTP 2 (H)', action='store_true')

		h('--anyauth', help='Pick "any" authentication method (H)', action='store_true')
		h('--basic', help='Use HTTP Basic Authentication (H)', action='store_true')
		h('--digest', help='Use HTTP Digest Authentication (H)', action='store_true')
		h('--ntlm', help='Use HTTP NTLM authentication (H)', action='store_true')
		h('--negotiate', help='Use HTTP Negotiate (SPNEGO) authentication (H)', action='store_true')

		a('--noproxy', help='List of hosts which do not use proxy', action='append')
		a('-x', '--proxy', metavar='(PROTOCOL://)HOST[:PORT]', help='Use proxy on given port')
		a('-U', '--proxy-user', metavar='USER[:PASSWORD]', help='Proxy user and password')
		a('--proxy1.0', metavar='HOST[:PORT]', help='Use HTTP/1.0 proxy on given port')
		a('-p', '--proxytunnel', help='Operate through a HTTP proxy tunnel (using CONNECT)', action='store_true')
		h('--proxy-anyauth', help='Pick "any" proxy authentication method (H)', action='store_true')
		h('--proxy-basic', help='Use Basic authentication on the proxy (H)', action='store_true')
		h('--proxy-digest', help='Use Digest authentication on the proxy (H)', action='store_true')
		h('--proxy-negotiate', help='Use HTTP Negotiate (SPNEGO) authentication on the proxy (H)', action='store_true')
		h('--proxy-ntlm', help='Use NTLM authentication on the proxy (H)', action='store_true')

		h('-d', '--data', metavar='DATA', help='HTTP POST data (H)')
		h('--data-ascii', dest='data', metavar='DATA', help='HTTP POST ASCII data (H)')
		h('--data-binary', metavar='DATA', help='HTTP POST binary data (H)')
		h('--data-urlencode', metavar='DATA', help='HTTP POST data url encoded (H)')
		h('-f', '--fail', help='Fail silently (no output at all) on HTTP errors (H)', action='store_true')
		h('-F', '--form', metavar='CONTENT', help='Specify HTTP multipart POST data (H)')
		h('--form-string', metavar='STRING', help='Specify HTTP multipart POST data (H)')
		h('-G', '--get', help='Send the -d data with a HTTP GET (H)', action='store_true')

		h('--ignore-content-length', help='Ignore the HTTP Content-Length header', action='store_true')
		h('-i', '--include', help='Include protocol headers in the output (H/F)', action='store_true')
		h('-k', '--insecure', help='Allow connections to SSL sites without certs (H)', action='store_true')
		h('-j', '--junk-session-cookies', help='Ignore session cookies read from file (H)', action='store_true')
		h('-L', '--location', help='Follow redirects (H)', action='store_true')
		h('--location-trusted', help='Like --location and send auth to other hosts (H)')
		h('--max-filesize', metavar='BYTES', help='Maximum file size to download (H/F)')
		h('--max-redirs', metavar='NUM', help='Maximum number of redirects allowed (H)')
		h('--no-alpn', help='Disable the ALPN TLS extension (H)', action='store_true')
		h('--no-npn', help='Disable the NPN TLS extension (H)', action='store_true')
		h('--post301', help='Do not switch to GET after following a 301 redirect (H)', action='store_true')
		h('--post302', help='Do not switch to GET after following a 302 redirect (H)', action='store_true')
		h('--post303', help='Do not switch to GET after following a 303 redirect (H)', action='store_true')
		h('--raw', help='Do HTTP "raw"; no transfer decoding (H)', action='store_true')
		h('-J', '--remote-header-name', help='Use the header-provided filename (H)')
		h('--tr-encoding', help='Request compressed transfer encoding (H)', action='store_true')

		# SSL
		s('--key', metavar='KEY', help='Private key file name (SSL/SSH)')
		s('--false-start', help='Enable TLS False Start.', action='store_true')
		s('--cacert', metavar='FILE', help='CA certificate to verify peer against (SSL)')
		s('--capath', metavar='DIR', help='CA directory to verify peer against (SSL)')
		s('-E', '--cert', metavar='CERT[:PASSWD]', help='Client certificate file and password (SSL)')
		s('--cert-status', help='Verify the status of the server certificate (SSL)', action='store_true')
		s('--cert-type', metavar='TYPE', help='Certificate file type (DER/PEM/ENG) (SSL)', choices=['DER', 'PEM', 'ENG'])
		s('--ciphers', metavar='LIST', help='SSL ciphers to use (SSL)')
		s('--egd-file', metavar='FILE', help='EGD socket path for random data (SSL)')
		s('--engine', metavar='ENGINE', help='Crypto engine (use "--engine list" for list) (SSL)')
		s('--key-type', metavar='TYPE', help='Private key file type (DER/PEM/ENG) (SSL)')
		s('--no-sessionid', help='Disable SSL session-ID reusing (SSL)', action='store_true')
		s('--random-file', metavar='FILE', help='File for reading random data from (SSL)')
		s('-2', '--sslv2', help='Use SSLv2 (SSL)', action='store_true')
		s('-3', '--sslv3', help='Use SSLv3 (SSL)', action='store_true')
		s('--ssl-allow-beast', help='Allow security flaw to improve interop (SSL)', action='store_true')
		s('-1', '--tlsv1', help='Use => TLSv1 (SSL)', action='store_true')
		s('--tlsv1.0', help='Use TLSv1.0 (SSL)', action='store_true')
		s('--tlsv1.1', help='Use TLSv1.1 (SSL)', action='store_true')
		s('--tlsv1.2', help='Use TLSv1.2 (SSL)', action='store_true')
		s('--tlsuser', metavar='USER', help='TLS username')
		s('--tlspassword', metavar='STRING', help='TLS password')
		s('--tlsauthtype', metavar='STRING', help='TLS authentication type (default: %(default)s)', default='SRP')
		s('--pass', metavar='PASS', help='Pass phrase for the private key (SSL/SSH)')
		s('--pinnedpubkey', metavar='FILE', help='Public key (PEM/DER) to verify peer against (OpenSSL/GnuTLS/GSKit only)')

		# F/SFTP
		f('-a', '--append', help='Append to target file when uploading (F/SFTP)', type=unsupported())
		f('--ftp-account', metavar='DATA', help='Account data string (F)', type=unsupported())
		f('--ftp-alternative-to-user', metavar='COMMAND', help='String to replace "USER [name]" (F)', type=unsupported())
		f('--ftp-create-dirs', help='Create the remote dirs if not present (F)', action='store_true')
		f('--ftp-method [MULTICWD/NOCWD/SINGLECWD]', help='Control CWD usage (F)', action='store_true')
		f('--ftp-pasv', help='Use PASV/EPSV instead of PORT (F)', action='store_true')
		f('-P', '--ftp-port', metavar='ADR', help='Use PORT with given address instead of PASV (F)', type=unsupported())
		f('--ftp-skip-pasv-ip', help='Skip the IP address for PASV (F)', action='store_true')
		f('--ftp-pret', help='Send PRET before PASV (for drftpd) (F)', action='store_true')
		f('--ftp-ssl-ccc', help='Send CCC after authenticating (F)', action='store_true')
		f('--ftp-ssl-ccc-mode', metavar='ACTIVE/PASSIVE', help='Set CCC mode (F)', type=unsupported())
		f('--ftp-ssl-control', help='Require SSL/TLS for FTP login, clear for transfer (F)', action='store_true')
		f('--disable-eprt', help='Inhibit using EPRT or LPRT (F)', action='store_true')
		f('--disable-epsv', help='Inhibit using EPSV (F)', action='store_true')
		f('--krb', metavar='LEVEL', help='Enable Kerberos with security LEVEL (F)', type=unsupported())
		f('--tftp-blksize', metavar='VALUE', help='Set TFTP BLKSIZE option (must be >512)')
		f('-Q', '--quote', metavar='CMD', help='Send command(s) to server before transfer (F/SFTP)')

		# Mail (SMTP, POP3, IMAP)
		m('-l', '--list-only', help='List only mode (F/POP3)', action='store_true')
		m('--login-options', metavar='OPTIONS', help='Server login options (IMAP, POP3, SMTP)')
		m('--mail-from', metavar='FROM', help='Mail from this address (SMTP)')
		m('--mail-rcpt', metavar='TO', help='Mail to this/these addresses (SMTP)')
		m('--mail-auth', metavar='AUTH', help='Originator address of the original email (SMTP)')
		m('--oauth2-bearer', metavar='TOKEN', help='OAuth 2 Bearer Token (IMAP, POP3, SMTP)')
		m('--ssl', help='Try SSL/TLS (FTP, IMAP, POP3, SMTP)', action='store_true')
		m('--ssl-reqd', help='Require SSL/TLS (FTP, IMAP, POP3, SMTP)', action='store_true')

		self.arguments = self.parser.parse_args()

	def unsupported(self, name=None):
		def _unsupported(value):
			if value:
				self.parser.error('--%s not yet supported' % (name,))
		return _unsupported


if __name__ == '__main__':
	Curl().run()
