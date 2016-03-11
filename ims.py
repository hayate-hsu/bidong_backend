'''
    cms : content manager system
    manager group
    manager account
    manager message
'''
from __future__ import absolute_import, division, print_function, with_statement

# Tornado framework
import tornado.web
HTTPError = tornado.web.HTTPError

import tornado.ioloop
import tornado.auth
import tornado.escape
import tornado.options
import tornado.locale
import tornado.util
import tornado.httpclient
import tornado.gen
import tornado.httputil

from tornado.util import errno_from_exception
from tornado.platform.auto import set_close_exec

from tornado.log import app_log

from tornado.options import define, options

define('port', default=8280, help='running on the given port', type=int)

import errno
import os
import sys
# import re

# import struct
# import hashlib
import socket
# import collections
import functools
# import time
import traceback

# import logging

# import xml.etree.ElementTree as ET

# Mako template
import mako.lookup
import mako.template

# from MySQLdb import (IntegrityError)


import util
_now = util.now

import settings
mas = settings['mas']

import imapi
import _const

json_encoder = util.json_encoder2
json_decoder = util.json_decoder

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
# TEMPLATE_PATH = settings['cms_path']
# MOBILE_PATH = os.path.join(TEMPLATE_PATH, 'm')

OK = {'Code':200, 'Msg':'OK'}

class Application(tornado.web.Application):
    '''
        Web application class.
        Redefine __init__ method.
    '''
    def __init__(self):
        handlers = [
            (r'/', IMHandler),
            (r'/notify', NotifyHandler),
        ]
        settings = {
            'cookie_secret':util.sha1('ims').hexdigest(), 
            # 'static_path':CURRENT_PATH,
            # 'static_url_prefix':'resource/',
            'debug':False,
            'autoreload':True,
            'autoescape':'xhtml_escape',
            # 'i18n_path':os.path.join(CURRENT_PATH, 'resource/i18n'),
            # 'login_url':'',
            'xheaders':True,    # use headers like X-Real-IP to get the user's IP address instead of
                                # attributeing all traffic to the balancer's IP address.
        }
        super(Application, self).__init__(handlers, **settings)

class BaseHandler(tornado.web.RequestHandler):
    '''
        BaseHandler
        override class method to adapt special demands
    '''
    LOOK_UP = mako.lookup.TemplateLookup(directories=[CURRENT_PATH, ], 
                                         module_directory='/tmp/ims/mako',
                                         output_encoding='utf-8',
                                         input_encoding='utf-8',
                                         encoding_errors='replace')
    # LOOK_UP_MOBILE = mako.lookup.TemplateLookup(directories=[MOBILE_PATH, ], 
    #                                             module_directory='/tmp/bidong/mako_mobile',
    #                                             output_encoding='utf-8',
    #                                             input_encoding='utf-8',
    #                                             encoding_errors='replace')

    RESPONSES = {}
    RESPONSES.update(tornado.httputil.responses)

    _IM_DISPATER = None
    @classmethod
    def __im__(cls):
        if not cls._IM_DISPATER:
            cls._IM_DISPATER = imapi.APIClient(mas['ip'], mas['user'], mas['password'], mas['code'])
        return cls._IM_DISPATER

    def initialize(self):
        '''
        '''
        pass

    def get_arguments(self, name, strip=True):
        assert isinstance(strip, bool)
        return self._get_arguments(name, self.request.arguments, strip)

    def _get_arguments(self, name, source, strip=True):
        values = []
        for v in source.get(name, []):
            if isinstance(v, basestring):
                v = self.decode_argument(v, name=name)
                if isinstance(v, tornado.escape.unicode_type):
                    v = tornado.web.RequestHandler._remove_control_chars_regex.sub(' ', v)
                if strip:
                    v = v.strip()
            values.append(v)
        return values

    def render_string(self, filename, **kwargs):
        '''
            Override render_string to use mako template.
            Like tornado render_string method, this method also
            pass request handler environment to template engine
        '''
        try:
            if not self.is_mobile():
                template = self.LOOK_UP.get_template(filename)
            else:
                template = self.LOOK_UP_MOBILE.get_template(filename)
            env_kwargs = dict(
                handler = self,
                request = self.request,
                # current_user = self.current_user
                locale = self.locale,
                _ = self.locale.translate,
                static_url = self.static_url,
                xsrf_form_html = self.xsrf_form_html,
                reverse_url = self.application.reverse_url,
            )
            env_kwargs.update(kwargs)
            return template.render(**env_kwargs)
        except:
            from mako.exceptions import RichTraceback
            tb = RichTraceback()
            for (module_name, line_no, function_name, line) in tb.traceback:
                print('File:{}, Line:{} in {}'.format(module_name, line_no, function_name))
                print(line)
            app_log.error('Render {} failed, {}:{}'.format(filename, tb.error.__class__.__name__, tb.error))
            raise HTTPError(500, 'Render page failed')

    def render(self, filename, **kwargs):
        '''
            Render the template with the given arguments
        '''
        template = CURRENT_PATH
        # if self.is_mobile():
        #     template = MOBILE_PATH
        if not os.path.exists(os.path.join(template, filename)):
            raise HTTPError(404, 'File Not Found')
        self.finish(self.render_string(filename, **kwargs))

    def set_status(self, status_code, reason=None):
        '''
            Set custom error resson
        '''
        self._status_code = status_code
        self._reason = 'Unknown Error'
        if reason is not None:
            self._reason = tornado.escape.native_str(reason)
        else:
            try:
                self._reason = self.RESPONSES[status_code]
            except KeyError:
                raise ValueError('Unknown status code {}'.format(status_code))

    def write_error(self, status_code, **kwargs):
        '''
            Customer error return format
        '''
        if self.settings.get('Debug') and 'exc_info' in kwargs:
            self.set_header('Content-Type', 'text/plain')
            # import traceback
            for line in traceback.format_exception(*kwargs['exc_info']):
                self.write(line)
            self.finish()
        else:
            self.render_json_response(Code=status_code, Msg=self._reason)
            # self.render('error.html', Code=status_code, Msg=self._reason)

    def render_json_response(self, **kwargs):
        '''
            Encode dict and return response to client
        '''
        # self.set_header('Access-Control-Allow-Origin', '*')
        callback = self.get_argument('callback', None)
        # check should return jsonp
        if callback:
            self.set_status(200, kwargs.get('Msg', None))
            self.finish('{}({})'.format(callback, json_encoder(kwargs)))
        else:
            self.set_status(kwargs['Code'], kwargs.get('Msg', None))
            self.set_header('Content-Type', 'application/json')
            self.finish(json_encoder(kwargs))

def _parse_body(method):
    '''
        Framework only parse body content as arguments 
        like request POST, PUT method.
        Through this method parameters can be send in uri or
        in body not matter request methods(contain 'GET', 'DELETE')
    '''
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        content_type = self.request.headers.get('Content-Type', '')

        # parse json format arguments in request body content
        if content_type.startswith('application/json') and self.request.body:
            arguments = json_decoder(tornado.escape.native_str(self.request.body))
            for name, values in arguments.iteritems():
                self.request.arguments.setdefault(name, []).extend([values,])
                # if isinstance(values, basestring):
                #     values = [values, ]
                # elif isinstance(values, dict):
                #     values = [values, ]
                # else:
                #     values = [v for v in values if v]
                # if values:
                #     self.request.arguments.setdefault(name, []).extend(values)
        # parse body if request's method not in (PUT, POST, PATCH)
        if self.request.method not in ('PUT', 'PATCH', 'POST'):
            if content_type.startswith('application/x-www-form-urlencode'):
                arguments = tornado.escape.parse_qs_bytes(
                    tornado.escape.native_str(self.request.body))
                for name, values in arguments.iteritems():
                    values = [v for v in values if v]
                    if values:
                        self.request.arguments.setdefault(name, []).extend(values)
            elif content_type.startswith('multipart/form-data'):
                fields = content_type.split(';')
                for field in fields:
                    k, sep, v = field.strip().partition('=')
                    if k == 'boundary' and v:
                        tornado.httputil.parse_multipart_form_data(
                            tornado.escape.utf8(v), self.request.body, 
                            self.request.arguments, self.request.files)
                        break
                    else:
                        app_log.error('Invalid multipart/form-data')
        return method(self, *args, **kwargs)
    return wrapper

def _trace_wrapper(method):
    '''
        Decorate method to trace logging and exception.
        Remarks : to make sure except catch and progress record
        _trace_wrapper should be the first decorator if a method
        is decorated by multiple decorators.
    '''
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            print('<-- In {}: <{}> -->'.format(self.__class__.__name__, self.request.method))
            return method(self, *args, **kwargs)
        except HTTPError:
            traceback.print_exc()
            raise
        except KeyError:
            if self.application.settings.get('debug', False):
                print(self.request)
            traceback.print_exc()
            raise HTTPError(400)
        except ValueError:
            if self.application.settings.get('debug', False):
                print(self.request)
            traceback.print_exc()
            raise HTTPError(400)
        except Exception:
            # Only catch normal exceptions
            # exclude SystemExit, KeyboardInterrupt, GeneratorExit
            traceback.print_exc()
            raise HTTPError(500)
        finally:
            print('<-- Out %s: <%s> -->\n\n'.format(self.__class__.__name__, self.request.method))
    return wrapper

class IMHandler(BaseHandler):
    '''
    '''
    @_trace_wrapper
    @_parse_body
    def post(self):
        mobile = self.get_argument('mobile')
        code = self.get_argument('code')
        im = self.__im__()
        try:
            im.send_sm(mobile, _const['msg_template'].format(code))
        except:
            traceback.print_exc()
            self.render_json_response(Code=400, Msg='Send message failed')
        else:
            self.render_json_response(**OK)

class NotifyHandler(BaseHandler):
    @_trace_wrapper
    @_parse_body
    def post(self):
        mobile = self.get_argument('mobile')
        msg = self.get_argument('msg')
        im = self.__im__()
        try:
            im.send_sm(mobile, msg.encode('utf-8'))
        except:
            traceback.print_exc()
            self.render_json_response(Code=400, Msg='Send message failed')
        else:
            self.render_json_response(**OK)

_DEFAULT_BACKLOG = 128
# These errnos indicate that a non-blocking operation must be retried
# at a later time. On most paltforms they're the same value, but on 
# some they differ
_ERRNO_WOULDBLOCK = (errno.EWOULDBLOCK, errno.EAGAIN)
if hasattr(errno, 'WSAEWOULDBLOCK'):
    _ERRNO_WOULDBLOCK += (errno.WSAEWOULDBLOCK, )

def bind_udp_socket(port, address=None, family=socket.AF_UNSPEC, backlog=_DEFAULT_BACKLOG, flags=None):
    '''
    '''
    udp_sockets = []
    if address == '':
        address = None
    if not socket.has_ipv6 and family == socket.AF_UNSPEC:
        family = socket.AFINET
    if flags is None:
        flags = socket.AI_PASSIVE
    bound_port = None
    for res in socket.getaddrinfo(address, port, family, socket.SOCK_DGRAM, 0, flags):
        af, socktype, proto, canonname, sockaddr = res
        try:
            sock = socket.socket(af, socktype, proto)
        except socket.error as e:
            if errno_from_exception(e) == errno.EAFNOSUPPORT:
                continue
            raise
        set_close_exec(sock.fileno())
        if os.name != 'nt':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if af == socket.AF_INET6:
            if hasattr(socket, 'IPPROTO_IPV6'):
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

        # automatic port allocation with port=None
        # should bind on the same port on IPv4 & IPv6 
        host, requested_port = sockaddr[:2]
        if requested_port == 0 and bound_port is not None:
            sockaddr = tuple([host, bound_port] + list(sockaddr[2:]))
        sock.setblocking(0)
        sock.bind(sockaddr)
        bound_port = sock.getsockname()[1]
        udp_sockets.append(sock)
    return udp_sockets

def add_udp_handler(sock, servers, io_loop=None):
    '''
        Read data in 4096 buffer
    '''
    if io_loop is None:
        io_loop = tornado.ioloop.IOLoop.current()
    def udp_handler(fd, events):
        while True:
            try:
                data, addr = sock.recvfrom(4096)
                if data:
                    # ac data arrived, deal with
                    pass
            except socket.error as e:
                if errno_from_exception(e) in _ERRNO_WOULDBLOCK:
                    # _ERRNO_WOULDBLOCK indicate we have accepted every
                    # connection that is avaiable
                    return
                import traceback
                traceback.print_exc(file=sys.stdout)
            except: 
                import traceback
                traceback.print_exc(file=sys.stdout)
    io_loop.add_handler(sock.fileno(), udp_handler, tornado.ioloop.IOLoop.READ)

def main():
    tornado.options.parse_command_line()

    ims_pid = os.path.join(settings['IMS_RUN_PATH'], 'p_{}.pid'.format(options.port))
    with open(ims_pid, 'w') as f:
        f.write('{}'.format(os.getpid()))

    app = Application()
    app.listen(options.port, xheaders=app.settings.get('xheaders', False))
    io_loop = tornado.ioloop.IOLoop.instance()
    app_log.info('IMS Server Listening:{} Started'.format(options.port))
    io_loop.start()

if __name__ == '__main__':
    main()
