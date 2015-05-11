from circuits.http.server import HTTP
from circuits.http.events import response as ResponseEvent
from circuits.net.sockets import TCPServer
from circuits import handler, BaseComponent, Debugger


class Resource(BaseComponent):
	@handler('request')
	def _on_request(self, client):
		client.response.body = str(client.request.uri)
		self.fire(ResponseEvent(client))


s = TCPServer(('localhost', 8090), channel='http.server')
h = HTTP(channel=s.channel)
s += h
s += Resource(channel=s.channel)
s += Debugger(events=True)

s.run()

###
# $ curl -i http://localhost:8090/path
#   HTTP/1.1 200 OK
#   Date: Mon, 11 May 2015 00:46:06 GMT
#   Content-Length: 5
#   Content-Type: text/plain; charset=UTF-8
#   Server: httoop/0.0
#
#   /path
