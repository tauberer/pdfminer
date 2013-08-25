#!/usr/bin/env python2
"""WebApp class runner

usage:
    $ runapp.py pdf2html.cgi

"""

import urllib.request, urllib.parse, urllib.error
import sys
from http.client import responses
from http.server import HTTPServer
from http.server import SimpleHTTPRequestHandler


class WebAppHandler(SimpleHTTPRequestHandler):

    APP_CLASS = None

    def do_POST(self):
        return self.run_cgi()

    def send_head(self):
        return self.run_cgi()

    def run_cgi(self):
        rest = self.path
        i = rest.rfind('?')
        if i >= 0:
            rest, query = rest[:i], rest[i + 1:]
        else:
            query = ''
        i = rest.find('/')
        if i >= 0:
            script, rest = rest[:i], rest[i:]
        else:
            script, rest = rest, ''
        scriptname = '/' + script
        scriptfile = self.translate_path(scriptname)
        uqrest = urllib.parse.unquote(rest)
        env = {
            'SERVER_SOFTWARE': self.version_string(),
            'SERVER_NAME': self.server.server_name,
            'GATEWAY_INTERFACE': 'CGI/1.1',
            'SERVER_PROTOCOL': self.protocol_version,
            'SERVER_PORT': str(self.server.server_port),
            'REQUEST_METHOD': self.command,
            'PATH_INFO': uqrest,
            'PATH_TRANSLATED': self.translate_path(uqrest),
            'SCRIPT_NAME': scriptname
        }
        if query:
            env['QUERY_STRING'] = query
        host = self.address_string()
        if host != self.client_address[0]:
            env['REMOTE_HOST'] = host
        env['REMOTE_ADDR'] = self.client_address[0]
        if self.headers.typeheader is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = self.headers.typeheader
        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length
        accept = []
        for line in self.headers.getallmatchingheaders('accept'):
            if line[:1] in "\t\n\r ":
                accept.append(line.strip())
            else:
                accept = accept + line[7:].split(',')
        env['HTTP_ACCEPT'] = ','.join(accept)
        ua = self.headers.getheader('user-agent')
        if ua:
            env['HTTP_USER_AGENT'] = ua
        co = [_f for _f in self.headers.getheaders('cookie') if _f]
        if co:
            env['HTTP_COOKIE'] = ', '.join(co)
        for k in ('QUERY_STRING', 'REMOTE_HOST', 'CONTENT_LENGTH',
                  'HTTP_USER_AGENT', 'HTTP_COOKIE'):
            env.setdefault(k, "")
        app = self.APP_CLASS(infp=self.rfile, outfp=self.wfile, environ=env)
        status = app.setup()
        self.send_response(status, responses[status])
        app.run()


def main(argv):
    import getopt
    import imp

    def usage():
        print('usage: %s [-h host] [-p port] [-n name] module.class' % argv[0])
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'h:p:n:')
    except getopt.GetoptError:
        return usage()
    host = ''
    port = 8080
    name = 'WebApp'
    for (k, v) in opts:
        if k == '-h':
            host = v
        elif k == '-p':
            port = int(v)
        elif k == '-n':
            name = v
    if not args:
        return usage()
    path = args.pop(0)
    module = imp.load_source('app', path)
    WebAppHandler.APP_CLASS = getattr(module, name)
    print('Listening %s:%d...' % (host, port))
    httpd = HTTPServer((host, port), WebAppHandler)
    httpd.serve_forever()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
