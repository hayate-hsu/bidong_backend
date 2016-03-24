'''
    special web application
    deploy with portal server in white name list
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

from tornado.options import define, options

#
define('port', default=8890, help='running on the given port', type=int)

import errno
import os
import sys
import re

# import struct
# import hashlib
import socket
# import collections
import functools
import time
import datetime

import logging

import xml.etree.ElementTree as ET

# Mako template
import mako.lookup
import mako.template

from MySQLdb import (IntegrityError)

import user_agents

logger = None

import util

_now = util.now

import settings

import account

json_encoder = util.json_encoder2
json_decoder = util.json_decoder

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_PATH = '/www/portal'
PAGE_PATH = os.path.join(TEMPLATE_PATH, 'm')


OK = {'Code':200, 'Msg':'OK'}

PN_POLICY = {}

class Application(tornado.web.Application):
    '''
        Web application class.
        Redefine __init__ method.
    '''
    def __init__(self):
        handlers = [
            (r'/account/(.*?)/bind', BindHandler),
            (r'/account/?(.*)$', AccountHandler),
            # (r'/m_web/(.*)', WeiXinViewHandler),
            (r'/(.*?\.html)$', PageHandler),
            # in product environment, use nginx to support static resources
            # (r'/(.*\.(?:css|jpg|png|js|ico|json))$', tornado.web.StaticFileHandler, 
            #  {'path':TEMPLATE_PATH}),
            # (r'/weixin$', WeiXinHandler),

            # register account
            (r'/register', RegisterHandler),

            # check version
            (r'/version', VersionHandler),

            # get mobile verify code
            (r'/mobile$', MobileHandler),

            # pns operator
            (r'/pns/', PNSHandler),

            # check ssid property
            (r'/ssid/(.*)$', WIFIHandler),

            # nansha interface
            # (r'/ns/manager', NSManagerHandler),
            # add/update/delete nansha employee
            # (r'/pn/(.*?)/(.*)$', PNAccountHandler),
            # (r'/pn/?(.*)$', PNHolderHandler),

            # group interface
            (r'/', MainHandler),
        ]
        settings = {
            'cookie_secret':util.sha1('bidong').hexdigest(), 
            'static_path':TEMPLATE_PATH,
            # 'static_url_prefix':'resource/',
            'debug':False,
            'autoreload':True,
            'autoescape':'xhtml_escape',
            'i18n_path':os.path.join(CURRENT_PATH, 'resource/i18n'),
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
    LOOK_UP = mako.lookup.TemplateLookup(directories=[TEMPLATE_PATH, ], 
                                         module_directory='/tmp/wnl/mako',
                                         output_encoding='utf-8',
                                         input_encoding='utf-8',
                                         encoding_errors='replace')
    LOOK_UP_MOBILE = mako.lookup.TemplateLookup(directories=[PAGE_PATH, ], 
                                                module_directory='/tmp/wnl/mako_mobile',
                                                output_encoding='utf-8',
                                                input_encoding='utf-8',
                                                encoding_errors='replace')

    RESPONSES = {}
    RESPONSES.update(tornado.httputil.responses)

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
            logger.error('Render {} failed, {}:{}'.format(filename, tb.error.__class__.__name__, tb.error), 
                         exc_info=True)
            raise HTTPError(500, 'Render page failed')

    def render(self, filename, **kwargs):
        '''
            Render the template with the given arguments
        '''
        template = TEMPLATE_PATH
        if self.is_mobile():
            template = PAGE_PATH
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
            import traceback
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
        callback = self.get_argument('callback', None)
        # check should return jsonp
        if callback:
            self.set_status(200, kwargs.get('Msg', None))
            self.finish('{}({})'.format(callback, json_encoder(kwargs)))
        else:
            self.set_status(kwargs['Code'], kwargs.get('Msg', None))
            self.set_header('Content-Type', 'application/json')
            self.finish(json_encoder(kwargs))

    def is_mobile(self):
        agent_str = self.request.headers.get('User-Agent', '')
        if not agent_str:
            return False

        if 'MicroMessenger' in agent_str:
            # from weixin client
            return True

        agent = user_agents.parse(agent_str)

        return agent.is_mobile

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
                        logger.warning('Invalid multipart/form-data')
        return method(self, *args, **kwargs)
    return wrapper

def _check_token(method):
    '''
        check user & token
    '''
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        user = self.get_argument('user') or self.get_argument('manager') 
        if not user:
            raise HTTPError(400, reason='account can\'t be null')
        token = self.get_argument('token')

        token, expired = token.split('|')
        token2 = util.token2(user, expired)
        if token != token2:
            raise HTTPError(400, reason='Abnormal token')
        # check expired?

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
            logger.info('<-- In %s: <%s> -->', self.__class__.__name__, self.request.method)
            return method(self, *args, **kwargs)
        except HTTPError:
            logger.error('HTTPError catch', exc_info=True)
            raise
        except KeyError:
            if self.application.settings.get('debug', False):
                print(self.request)
            logger.warning('Arguments error', exc_info=True)
            raise HTTPError(400)
        except ValueError:
            if self.application.settings.get('debug', False):
                print(self.request)
            logger.warning('Arguments value abnormal', exc_info=True)
            raise HTTPError(400)
        except Exception:
            # Only catch normal exceptions
            # exclude SystemExit, KeyboardInterrupt, GeneratorExit
            logger.error('Unknow error', exc_info=True)
            raise HTTPError(500)
        finally:
            logger.info('<-- Out %s: <%s> -->\n\n', self.__class__.__name__, self.request.method)
    return wrapper

class MainHandler(BaseHandler):
    '''
    '''
    @_trace_wrapper
    def get(self):
        self.render('index.html')

class PageHandler(BaseHandler):
    '''
    '''
    @_trace_wrapper
    @_parse_body
    def get(self, page):
        '''
            Render html page
        '''
        page = page.lower()
        # if not page.endswith('.html'):
        #     page = page + '.html'
        # if page.startswith('manager.html'):
        #     return self.render('login_admin.html')        
        return self.render(page)

class AccountHandler(BaseHandler):
    '''
        process bd account
    '''
    def check_token(self, user, token):
        token,expired = token.split('|')
        token2 = util.token2(user, expired)
        if token != token2:
            raise HTTPError(400, reason='Abnormal token')

    @_trace_wrapper
    @_parse_body
    def get(self, user):
        token = self.get_argument('token')
        self.check_token(user, token)
        _user, renters = None, None
        _user = account.get_bd_account(user)
        # _user.pop('password', 0)
        if not _user:
            raise HTTPError(404, reason='account not existed')

        days, hours = util.format_left_time(_user['expire_date'], _user['coin'])

        accept = self.request.headers.get('Accept', 'text/html')
        if accept.startswith('application/json'):
            self.render_json_response(Account=_user, days=days, hours=hours, **OK)
        else:
            self.render('mybidong.html', token=token, 
                        days=days, hours=hours, **_user)
    
    @_trace_wrapper
    @_parse_body
    def post(self, user=None):
        user = self.get_argument('user')
        password = self.get_argument('password')

        _user = account.get_bd_account(user)
        if not _user:
            raise HTTPError(404, reason='account not existed')

        # if password != _user['password']:
        # if _user['password'] not in (password, util.md5(password).hexdigest(), util.md5(_user['password']).hexdigest()):
        if password not in (_user['password'], util.md5(_user['password']).hexdigest()):
            raise HTTPError(403, reason='password error')

        token = util.token(user)

        _user.pop('password', '')
        self.render_json_response(User=_user['user'], Token=token, **OK)

    @_trace_wrapper
    @_parse_body
    def put(self, user):
        '''
            update bd_account's info
        '''
        token = self.get_argument('token')
        self.check_token(user, token)
        _user = account.get_bd_account(user)
        if not _user:
            raise HTTPError(404, reason='account not existed')

        kwargs = {}
        newp = self.get_argument('newp', '')
        if newp:
            # chanage password
            password = self.get_argument('password')
            if password != _user['password']:
                raise HTTPError(403, reason='password error')
            kwargs['password'] = newp

        account.update_account(user, **kwargs)
        self.render_json_response(**OK)

    @_trace_wrapper
    @_parse_body
    def delete(self, user):
        '''
            delete account & wireless login history
        '''
        token = self.get_argument('token')
        self.check_token(user, token)
        _user = account.get_bd_account(user)
        if not _user:
            raise HTTPError(404, reason='account not existed')
        
        # mask = int(self.get_argument('mask', 0))
        account.remove_account(user, 1)

        self.render_json_response(**OK)

class BindHandler(AccountHandler):
    '''
    '''
    def check_token(self, user):
        if not user:
            raise HTTPError(400, reason='account can\'t be null')
        token = self.get_argument('token')

        token, expired = token.split('|')
        token2 = util.token2(user, expired)
        if token != token2:
            raise HTTPError(400, reason='Abnormal token')

    @_trace_wrapper
    @_parse_body
    # @_check_token
    def post(self, user):
        self.check_token(user)
        flags = int(self.get_argument('flags', 0))
        if not flags:
            self.bind_room(user)
        else:
            self.bind_mobile(user)

    # current desn't open unbind interface to client
    # @_trace_wrapper
    # @_parse_body
    # def delete(self, user):
    #     self.check_token(user)
    #     flags = int(self.get_argument('flags', 0))
    #     if not flags:
    #         # unbind room
    #         self.unbind_room(user)
    #     else:
    #         # unbind mobile number
    #         self.unbind_mobile(user)

    def bind_mobile(self, user):
        mobile = self.get_argument('mobile')
        pn = self.get_argument('pn', '')
        
        account.update_account(user, mobile=mobile)

        if pn and account.get_pn_account(pn, mobile=mobile):
            account.bind_pn_account(pn, user, mobile)

        self.render_json_response(**OK)


    def unbind_mobile(self, user):
        mobile = self.get_argument('mobile')
        pn = self.get_argument('pn', '')
        
        # set '' to mobile field
        # account.update_account(user, mobile='')
        if pn and account.get_pn_account(pn, mobile=mobile):
            account.unbind_pn_account(pn, mobile)

        self.render_json_response(**OK)

    def bind_room(self, user):
        room = self.get_argument('room') 
        password = self.get_argument('password')

        # check room & password
        _user = account.get_bd_account(room)
        if (not _user) or (password != _user['password']):
            raise HTTPError(401, reason='Please check your room and password')
        
        account.bind(user, room)
        _user = account.get_bd_account(user)
        days, hours = util.format_left_time(_user['expire_date'], _user['coin'])
        self.render_json_response(days=days, hours=hours, **OK)

    def unbind_room(self, user):
        room = self.get_argument('room')
        # password = self.get_argument('password')

        # check room & password
        _user = account.get_bd_account(room)
        if not _user:
            raise HTTPError(401, reason='Please check your room')

        account.unbind(user, room)

        self.render_json_response(**OK)

class MobileHandler(BaseHandler):
    '''
        verify mobile and send verify code
    '''
    MOBILE_PATTERN = re.compile(r'^(?:13[0-9]|14[57]|15[0-35-9]|17[678]|18[0-9])\d{8}$')
    URL = 'http://14.23.171.10/'

    @_trace_wrapper
    @tornado.gen.coroutine
    @_parse_body
    def post(self):
        '''
            check mobile and send verify code to user
            client check mobile number
        '''
        mobile = self.get_argument('mobile')
        if not self.check_mobile(mobile):
            raise HTTPError(400, reason='invalid mobile number')
        pn, ssid = '', ''
        pn = self.get_argument('pn', '')
        if pn:
            # check private network, if existed pn, return ssid & pn 
            record = account.get_pn_account(pn, mobile=mobile)
            if record:
                ssid = record['ssid']
            else:
                raise HTTPError(403, reason='no privilege')
                # get pn's private network ssid
        # flags = self.get_argument('flags', 0)
        # if flags == 1:
        #     # check account is nansha employee account
        #     record = account.get_ns_employee(mobile=mobile)
        #     if not record:
        #         raise HTTPError(403, reason='mobile is not nansha employee')
        #         # return self.render_json_response(Code=403, Msg='mobile not nansha employee')
        # isNS = 1 if account.get_ns_employee(mobile=mobile) else 0

        
        verify = util.generate_verify_code()
        mask = self.get_argument('mask', 0)
        # mask: 4 - web portal platform 
        if mask>>2 & 1:
            code = util.md5(verify).hexdigest()[-8:]
            verify = code[12:16] + code[-4:]
            self.render_json_response(verify=verify, pn=pn, ssid=ssid, **OK)
        else:
            self.render_json_response(verify=verify, pn=pn, ssid=ssid, **OK)

        # send verify code to special mobile
        data = json_encoder({'mobile':mobile, 'code':verify})
        request = ''
        request = tornado.httpclient.HTTPRequest(MobileHandler.URL, method='POST', 
                                                 headers={'Content-Type':'application/json'}, 
                                                 body=data)
        http_client = tornado.httpclient.AsyncHTTPClient() 
        response = yield http_client.fetch(request)
        if response.code != 200:
            raise response.error

    def check_mobile(self, mobile):
        return True if re.match(MobileHandler.MOBILE_PATTERN, mobile) else False

class VersionHandler(BaseHandler):
    '''
        check app's version
    '''
    @_trace_wrapper
    @_parse_body
    def get(self):
        '''
            if ver is True, check version
            return version record (contain mask)
        '''
        mask = int(self.get_argument('mask'))
        ver = self.get_argument('version', '')
        record = account.get_version(mask)
        if not record:
            raise HTTPError(400)
        if ver:
            newest, least = self.check_version(ver, record)
            record['mask'] = (1 if newest else 0) + (2 if least else 0)

        self.render_json_response(Code=200, Msg='OK', **record)

    @_trace_wrapper
    @_parse_body
    def post(self):
        mask = int(self.get_argument('mask'))
        ver = self.get_argument('version')
        note = self.get_argument('note', '')

        account.create_version(ver, mask, note)
        self.render_json_response(Code=200, Msg='OK')

    @_trace_wrapper
    @_parse_body
    def put(self):
        mask = int(self.get_argument('mask'))
        kwargs = {}
        kwargs['newest'] = self.get_argument('newest', '')
        kwargs['least'] = self.get_argument('least', '')
        kwargs['note'] = self.get_argument('note', '')
        for key in kwargs.keys():
            if not kwargs[key]:
                kwargs.pop(key)
        if kwargs:
            account.update_version(mask, **kwargs)

        self.render_json_response(**OK)

    def check_version(self, ver, record):
        '''
            return: the newest version, the least avaiable version
        '''
        ver = [int(item) for item in ver.split('.')]
        least = [int(item) for item in record['least'].split('.')]
        newest = [int(item) for item in record['newest'].split('.')]
        return ver>=newest, ver>=least

#***************************************************
#
#   
#     Nansha city handler
#
#
#****************************************************
class RegisterHandler(BaseHandler):
    '''
    '''
    @_trace_wrapper
    @_parse_body
    def post(self):
        mask = int(self.get_argument('mask'))
        if mask>>8 & 1:
            pass
        uuid = self.get_argument('uuid')
        _account = account.get_account(uuid=uuid)
        _id = ''
        if not _account:
            # can't found, create new account
            _id = account.create_app_account(uuid, mask)
        else:
            _id = _account['id']
        _user = account.get_bd_account(_id)
        
        return self.render_json_response(Code=200, Msg='OK', **_user)

class PNSHandler(BaseHandler):
    '''
    '''
    @_trace_wrapper
    @_parse_body
    @_check_token
    def get(self):
        '''
            query pns which user can access
        '''
        pns = account.get_pns()

        self.render_json_response(pns=pns, **OK)

    @_trace_wrapper
    @_parse_body
    @_check_token
    def post(self):
        '''
            bind user account and pns
        '''
        user = self.get_argument('user')
        mobile = self.get_argument('mobile')
        # pns = self.get_arguments('pns')

        pns = account.bind_avaiable_pns(user, mobile)

        if not pns:
            raise HTTPError(404)

        self.render_json_response(pns=pns, **OK)

class WIFIHandler(BaseHandler):
    '''
    '''
    @_trace_wrapper
    @_parse_body
    def get(self, ssid):
        '''
        '''
        mac = self.get_argument('mac').upper()
        isys, record = account.check_ssid(ssid, mac)

        if not record:
            return self.render_json_response(isys=isys, ispri=0, Code=200, Msg='OK')
        else:
            return self.render_json_response(isys=isys, Code=200, Msg='OK', **record)

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
    global logger
    tornado.options.parse_command_line()
    import trace
    trace.init(settings['LOG_PORTAL_PATH'], options.port)
    logger = trace.logger('bidong', False)
    logger.setLevel(logging.INFO)

    bidong_pid = os.path.join('/var/run/', 'sportal/p_{}.pid'.format(options.port))
    with open(bidong_pid, 'w') as f:
        f.write('{}'.format(os.getpid()))

    app = Application()
    app.listen(options.port, xheaders=app.settings.get('xheaders', False))
    io_loop = tornado.ioloop.IOLoop.instance()
    logger.info('Special Server Listening : {} Started'.format(options.port))
    io_loop.start()

if __name__ == '__main__':
    main()
