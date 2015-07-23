'''
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

from tornado.options import define, options

define('port', default=8080, help='running on the given port', type=int)

import errno
import os
import sys

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
import _const

json_encoder = util.json_encoder
json_decoder = util.json_decoder

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_PATH = settings['src_path']
MOBILE_PATH = os.path.join(TEMPLATE_PATH, 'm')

OK = {'Code':200, 'Msg':'OK'}

class Application(tornado.web.Application):
    '''
        Web application class.
        Redefine __init__ method.
    '''
    def __init__(self):
        handlers = [
            (r'/account/(.*?)/bind', BindHandler),
            (r'/account/?(.*)$', AccountHandler),
            (r'/m_web/(.*)', WeiXinViewHandler),
            (r'/(getdbi)\.html', FactoryHandler),
            (r'/(.*?\.html)$', PageHandler),
            # in product environment, use nginx to support static resources
            # (r'/(.*\.(?:css|jpg|png|js|ico|json))$', tornado.web.StaticFileHandler, 
            #  {'path':TEMPLATE_PATH}),
            (r'/weixin$', WeiXinHandler),
            (r'/holder/(.*)/ap$', APHandler),
            (r'/holder/(.*)/room$', RoomHandler),
            (r'/holder/?(.*)$', HolderHandler),
            (r'/manager/?(.*)$', ManagerHandler),
            # (r'/test', TestHandler),
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
                                         module_directory='/tmp/bidong/mako',
                                         output_encoding='utf-8',
                                         input_encoding='utf-8',
                                         encoding_errors='replace')
    LOOK_UP_MOBILE = mako.lookup.TemplateLookup(directories=[MOBILE_PATH, ], 
                                                module_directory='/tmp/bidong/mako_mobile',
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
            template = MOBILE_PATH
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

def create_menu():
    '''
        Create menu
    '''
    import menu
    print(menu)
    url = '{}/menu/create?access_token'.format(WeiXinHandler.BASE_URL, WeiXinHandler.get_token())
    client = tornado.httpclient.HTTPClient()
    response = client.fetch(url, connect_timeout=5, request_timeout=15)
    result = json_decoder(response.body)
    if not result['errcode']:
        # create menu successfully
        return
    # error
    logger.error('Create menu failed, ret: {}'.format(result))

class WeiXinViewHandler(BaseHandler):
    '''
        /m_web/(.*)
    '''
    WEIXIN_CONFIG = settings['weixin']
    _WX_IP = 'api.weixin.qq.com'
    for family,type,proto,canonname,sockaddr in socket.getaddrinfo('api.weixin.qq.com', None, socket.AF_INET, 0, socket.SOL_TCP):
        _WX_IP = sockaddr[0]
        break
    URL = ''.join(['https://', _WX_IP, '/sns/oauth2/access_token?appid={}&secret={}&code={}&grant_type=authorization_code'])

    _ACTION = ['onttonet', 'earn_coin', 'join_us']

    @property
    def dispatch(self):
        return {
            'onetonet':self.auto_login,
            'earn_coin':self.earn_coin,
            'join_us':self.join_us,
            }

    @_trace_wrapper
    @tornado.gen.coroutine
    def get(self, action=None):
        '''
        '''
        print(self.request)
        code = self.get_argument('code', '')
        if not code:
            # user forbid
            pass
        url = self.URL.format(self.WEIXIN_CONFIG['appid'], self.WEIXIN_CONFIG['secret'], code)
        client = tornado.httpclient.AsyncHTTPClient()
        # client = tornado.httpclient.HTTPClient()
        response = yield client.fetch(url, allow_nonstandard_methods=True)
        
        result = json_decoder(response.body)

        self._check_weixin_account(result['openid'])

        self.dispatch[action](result['openid'])


    def auto_login(self, openid):
        _user = account.get_account_by_openid(openid)
        if not _user:
            return self.render('error.html', Msg=_const[404])
        # if not _user['mask']>>1 & 1:
        #     return self.render('error.html', Msg=_const[453])

        _user = account.get_bd_account(_user['id'])
        # _user.pop('password', 0)
        if not _user:
            raise HTTPError(404, reason='account not existed')

        # days, hours = util.format_left_time(_user['expire_date'], _user['coin'])
        token = util.token(_user['user'])
        self.redirect('/account/{}?token={}'.format(_user['user'], token))

    def get_holder(self, openid):
        _user = account.get_account_by_openid(openid)
        if not _user:
            return self.render('error.html', Msg=_const[404])
        if not _user['mask']>>1 & 1:
            return self.render('error.html', Msg=_const[453])
        token = util.token(_user['user'])

        self.redirect('/holder/{}?token={}'.format(_user['user'], token))

    def _check_weixin_account(self, openid):
        _user = account.get_account_by_openid(openid)
        if not _user:
            account.create_weixin_account(openid)

    @_trace_wrapper
    def earn_coin(self, openid):
        _user = account.get_account_by_openid(openid)
        if not _user:
            return self.render('error.html', Msg=_const[404])

        # _user = account.get_bd_account(_user['id'])
        # if not _user:
        #     return self.render('error.html', Msg='account not existed')

        token = util.token(str(_user['id']))
        self.redirect('/getdbi.html?user={}&token={}'.format(_user['id'], token))

    def join_us(self, openid):
        self.render('joinus.html', Openid=openid)

class WeiXinHandler(BaseHandler):
    '''
    '''
    # weixin open account's info
    WEIXIN_CONFIG = settings['weixin']
    _WX_IP = 'api.weixin.qq.com'
    for family,type,proto,canonname,sockaddr in socket.getaddrinfo('api.weixin.qq.com', None, socket.AF_INET, 0, socket.SOL_TCP):
        _WX_IP = sockaddr[0]
        break
    WEIXIN_CONFIG = settings['weixin']
    BASE_URL = 'https://api/{}/cgi-bin'.format(_WX_IP)
    URLS = {
        # 'create_menu':'{}/menu/create?access_token={}'.format(BASE_URL, WeiXinHandler.get_token()),
        'access_token':'{}/token?grant_type={}&appid={}&secret={}'.format(BASE_URL, 
                                                                          WEIXIN_CONFIG['grant_type'], 
                                                                          WEIXIN_CONFIG['appid'], 
                                                                          WEIXIN_CONFIG['secret']),
    }

    TOKEN = {'account_token':'', 'expire_seconds':0}
    # read token
    _token_path = os.path.join(CURRENT_PATH, 'token.cnf')
    if os.path.exists(_token_path):
        with open(_token_path, 'r') as f:
            TOKEN = json_decoder(f.read())

    @classmethod
    def get_token(cls):
        '''
            access weixin server to get access_token.
            the special request is blocking. so all WeixinHandler
            instance can share the same avaiable token
        '''
        if int(time.time()) < cls.TOKEN['expire_seconds']:
            return cls.TOKEN('access_token')
        else:
            # if token expired, get new token
            client = tornado.httpclient.HTTPClient()
            response = client.fetch(cls.URLS['access_token'], connect_timeout=5, request_timeout=15)
            result = json_decoder(response.body)
            if 'access_token' in result:
                # 2 minutes redundance
                cls.TOKEN['expire_seconds'] = int(time.time()) + cls.WEIXIN_CONFIG['expire'] - 120
                cls.TOKEN['access_token'] = result['access_token']
                with open(cls._token_path, 'w') as f:
                    f.write(json_encoder(cls.TOKEN))
                return cls.TOKEN('access_token')
            # get access_token error
            logger.error('get access_token error, ret: {}'.format(result))
            raise HTTPError(500)

    def prepare(self):
        '''
            all request must be check request's issuer
        '''
        signature = self.get_argument('signature')
        timestamp = self.get_argument('timestamp')
        nonce = self.get_argument('nonce')

        sha1 = util.sha1(''.join(sorted([self.WEIXIN_CONFIG['_TOKEN_'], timestamp, nonce])))
        if signature != sha1.hexdigest():
            raise HTTPError(400)
    
    @_trace_wrapper 
    @_parse_body
    def get(self):
        echostr = self.get_argument('echostr')
        self.finish(echostr)

    def xml_response(self, request, user, **kwargs):
        '''
        '''
        response = '''<xml>
        <ToUserName><![CDATA[{}]]></ToUserName>
        <FromUserName><![CDATA[{}]]></FromUserName>
        <CreateTime>{}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[{}]]></Content>
        </xml>
        '''
        days, hours = 0,'00:00'
        # check current data
        if user['expire_date']:
            _expire_datetime = datetime.datetime.strptime(user['expire_date'], '%Y-%m-%d')
            delta = _expire_datetime - datetime.datetime.now()
            days = delta.days
            if days < 0:
                days = 0
            else:
                days = days + 1

        if user['coin']>0:
            # one coin = 3 minutes
            times = user['coin']*3*60
            hours = '{:02d}:{:02d}'.format(int(times/3600), int(times%3600/60))
        # self.finish(response.format(request['FromUserName'], request['ToUserName'], int(time.time()), 
        #                             'User : {}\nPassword : {}'.format(user['user'], user['password'])))
        data = response.format(request['FromUserName'], request['ToUserName'], int(time.time()), 
                               '''\xe8\xb4\xa6\xe5\x8f\xb7 : {}\n\xe5\xaf\x86\xe7\xa0\x81 : {}\n\xe5\x8f\xaf\xe7\x94\xa8\xe4\xb8\x8a\xe7\xbd\x91\xe6\x97\xb6\xe9\x95\xbf: {}\xe5\xa4\xa9 + {}'''.format(user['user'], user['password'], days, hours))
        self.finish(data)

    @_trace_wrapper
    @_parse_body
    def post(self):
        '''
            parse client's message, then return correspond response
        '''
        root = ET.fromstring(self.request.body) 
        request = {item.tag:item.text for item in list(root)}
        # request = {item.tag:item.text for item in list(root)}
        print(request)
        if request['MsgType'] == 'event':
            #
            if request['Event'] == 'CLICK':
                if request['EventKey'] == 'V1001_NET_ACCOUNT':
                    # query online account and return account
                    self._check_weixin_account(request['FromUserName'])
                    _user = account.get_weixin_account(request['FromUserName'])
                    return self.xml_response(request, _user)
            if request['Event'] == 'subscribe':
                # check FromUserName & ToUserName 
                account.create_weixin_account(request['FromUserName'])
                return self.finish()
            if request['Event'] == 'unsubscribe':
                account.remove_weixin_account(request['FromUserName'])
                return self.finish()
            if request['Event'] == 'VIEW':
                # self._check_weixin_account(request['FromUserName'])
                pass
        else:
            print(request['MsgType'])
        self.finish()

    def _check_weixin_account(self, openid):
        _user = account.get_account_by_openid(openid)
        if not _user:
            account.create_weixin_account(openid)

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

class AccountBaseHandler(BaseHandler):
    '''
        Account base handler
        check token
    '''
    def check_token(self, user, token):
        token, expired = token.split('|')
        token2 = util.token2(user, expired)
        if token != token2:
            raise HTTPError(400)

    def check_holder(self, holder):
        '''
            check account type
            holder/ap/room manager handler need this function to
            check holder account
        '''
        _user = account.get_account(holder)
        if not _user:
            raise HTTPError(404)
        if not _user['mask']>>1 & 1:
            raise HTTPError(404, 'Not Holder')
        return _user

class ManagerHandler(AccountBaseHandler):
    '''
    '''
    @_trace_wrapper
    @_parse_body
    def get(self, action=None):
        '''
        '''
        token,manager='',''
        action = action.strip('/')
        try:
            token = self.get_argument('token')
            manager = self.get_argument('manager')
        except tornado.web.MissingArgumentError:
            return self.redirect('/manager.html')
        self.check_token(manager, token)

        if not action:
            return self.render('admin.html', manager=manager, token=token)

        # logger.info('Manager: {} operatr {}'.format(manager, action))
        if action == 'holder':
            self.holder()
        elif action == 'ap':
            self.ap()

    @_trace_wrapper
    @_parse_body
    def post(self, action=None):
        '''
        '''
        if action:
            token = self.get_argument('token')
            manager = self.get_argument('manager')
            # check manager token
            self.check_token(manager, token)
            ids = []
            # add holder & ap records
            if action == 'holder':
                holders = self.get_argument('holders')
                for holder in holders:
                    _id = account.create_holder('', holder['mobile'], holder['address'], holder['realname'])
                    if _id:
                        # verify holder
                        account.verify_holder(_id, expire_date=holder['expire_date'], mask=3, verify=1)
                        ids.append(_id)
            elif action == 'ap':
                aps = self.get_argument('aps', [])
                # kwargs = {}
                # kwargs['vendor'] = self.get_argument('vendor')
                # kwargs['model'] = self.get_argument('model')
                # kwargs['mac'] = self.get_argument('mac')
                # kwargs['profile'] = self.get_argument('profile')
                # kwargs['fm'] = self.get_argument('fm')
                # ap deploy position
                # kwargs['point'] = (100, 99)
                for ap in aps:
                    try:
                        account.create_ap(**ap)
                    except IntegrityError:
                        logger.warning('ap\'s mac exsited: {}'.format(ap['mac']))
                        raise HTTPError(400, reason='mac address existed')
            else:
                raise HTTPError(400)
            self.render_json_response(Ids=ids, **OK)
        else:
            # manager login
            user = self.get_argument('user')
            password = self.get_argument('password')

            _user = account.get_manager(user)
            if not _user:
                raise HTTPError(404, reason='account not existed')
            if password != _user['password']:
                raise HTTPError(400, reason='password error')
                    
            token = util.token(user)
            content_type = self.request.headers.get('Content-Type', '')
            if content_type.startswith('application/json'):
                self.render_json_response(Manager=user, Token=token, **OK)
            else:
                self.redirect('/manager?token={}&manager={}'.format(token, user))

    @_trace_wrapper
    @_parse_body
    def put(self, action=None):
        '''
        '''
        token = self.get_argument('token')
        manager = self.get_argument('manager')
        # check manager token
        self.check_token(manager, token)

        if action == 'holder':
            holders = self.get_argument('holders')
            for holder in holders:
                account.verify_holder(holder.pop('id'), **holder)
        elif action == 'ap':
            aps = self.get_argument('aps')
            for ap in aps:
                account.update_ap(ap.pop('mac'), **ap)
        elif action == 'bind_ap':
            holder = self.get_argument('holder')
            aps = self.get_argument('aps')
            account.bind_aps(holder, aps)
        elif action == 'unbind_ap':
            holder = self.get_argument('holder')
            aps = self.get_argument('aps')
            account.unbind_aps(holder, aps)


        self.render_json_response(**OK)

    
    @_trace_wrapper
    @_parse_body
    def delete(self, action=None):
        '''
        '''
        token = self.get_argument('token')
        manager = self.get_argument('manager')
        # check manager token
        self.check_token(manager, token)

        if action == 'holder':
            holder = self.get_argument('id')
            account.remove_holder(holder)
        elif action == 'ap':
            aps = self.get_argument('aps')
            account.remove_aps(aps)

        self.render_json_response(**OK)

    @_trace_wrapper
    def holder(self):
        '''
            get unverified holder
            mask : 
        '''
        page = int(self.get_argument('page', 0))
        verified = int(self.get_argument('verified', 0))
        pages, holders = account.get_holders(page, verified)
        if page == 0:
            return self.render_json_response(Code=200, Msg='OK', Holders=holders, Pages=pages)
        return self.render_json_response(Code=200, Msg='OK', Holders=holders, Pages=pages)

    @_trace_wrapper
    def ap(self):
        '''
            get ap
                holder's ap
                special ap
        '''
        # holder = self.get_argument('holder', '')
        # mac = self.get_argument('mac', '')
        # default query holder's aps
        field = 'holder'
        query = self.get_argument('field')
        if ':' in query:
            # query special ap 
            field = 'mac'

        records = account.get_aps(field, query)
        self.render_json_response(aps=records, **OK)

    def room(self, holder):
        '''
        '''
        _user, renters = account.get_renters(holder)
        rooms = [item['room'] for item in renters]
        rooms = sorted(rooms)
        return self.render_json_response(Code=200, Msg='OK', Rooms=rooms)

class TestHandler(BaseHandler):
    @_trace_wrapper
    def post(self):
        '''
        '''
        self.finish('hello world')

class FactoryHandler(AccountBaseHandler):
    @_trace_wrapper
    def get(self, resource):
        user = self.get_argument('user')
        token = self.get_argument('token')
        self.check_token(user, token)
        _user = account.get_bd_account(user)
        # _user.pop('password', 0)
        if not _user:
            raise HTTPError(404, reason='account not existed')

        days, hours = util.format_left_time(_user['expire_date'], _user['coin'])
        accept = self.request.headers.get('Accept', 'text/html')
        if accept.startswith('application/json'):
            self.render_json_response(Account=_user, **OK)
        else:
            self.render(resource+'.html', token=token, 
                        days=days, hours=hours, **_user)

class AccountHandler(AccountBaseHandler):
    '''
        process bd account
    '''
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

        # days, hours = 0,'00:00'
        # # check current data
        # if _user['expire_date']:
        #     _expire_datetime = datetime.datetime.strptime(_user['expire_date'], '%Y-%m-%d')
        #     delta = _expire_datetime - datetime.datetime.now()
        #     days = delta.days
        #     if days < 0:
        #         days = 0
        #     else:
        #         days = days + 1

        # if _user['coin']>0:
        #     # one coin = 3 minutes
        #     times = _user['coin']*3*60
        #     hours = '{:02d}:{:02d}'.format(int(times/3600), int(times%3600/60))

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
        if password != _user['password']:
            raise HTTPError(403, reason='password error')

        token = util.token(user)

        
        _user.pop('possword', '')
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
            password = self.get_argument('password')
            if password != _user['password']:
                raise HTTPError(403, reason='password error')
            kwargs['password'] = newp

        account.update_account(user, **kwargs)
        self.render_json_response(**OK)


class BindHandler(AccountBaseHandler):
    '''
    '''
    @_trace_wrapper
    @_parse_body
    def post(self, user):
        token = self.get_argument('token')
        self.check_token(user, token)
        # room : (holder+room)
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

class HolderHandler(AccountBaseHandler):
    '''
        Holder manage handler
    '''
    @_trace_wrapper
    @_parse_body
    def get(self, holder):
        '''
        '''
        token = self.get_argument('token')
        self.check_token(holder, token)
        holder = int(holder)
        self.check_holder(holder)
        # get bd_account
        # _user = account.get_bd_account(holder)

        # get renters
        _user, renters = account.get_renters(holder)
        _user.pop('possword', '')
        logger.info('test: {}'.format(self.request))

        accept = self.request.headers.get('Accept', 'text/html')
        if accept.startswith('application/json'):
            self.render_json_response(Account=_user, Renters=renters, **OK)
        else:
            _user['mobile'] = ''.join([_user['mobile'][:3], '****', _user['mobile'][7:]])
            _user['realname'] = _user['realname'][0] + ' **'
            self.render('addclient.html', token=token, date=_now('%Y-%m-%d'), 
                        renters=renters, **_user)

    @_trace_wrapper
    @_parse_body
    def post(self, holder=None):
        '''
            create holder account
            mobile,address,realname must set
        '''
        weixin = self.get_argument('openid', '')
        mobile = self.get_argument('mobile')
        address = self.get_argument('address')
        realname = self.get_argument('realname')
        # email = self.get_argument('email', '')
        _id = account.create_holder(weixin, mobile, address, realname)
        self.render_json_response(ID=_id, **OK)

    @_trace_wrapper
    @_parse_body
    def put(self, holder):
        '''
            Update holder 's account
        '''
        raise HTTPError(405)
        holder = int(holder)
        self.check_holder(holder)

        # manager = self.get_argument('manager')
        # token = self.get_argument('token')
        manager = self.get_secure_cookie('manager')
        token = self.get_secure_cookie('m_token')

        self.check_token(manager, token)

        fields = {}
        # fields['weixin'] = self.get_argument('weixin', '')
        fields['mobile'] = self.get_argument('mobile')
        fields['address'] = self.get_argument('address')
        fields['realname'] = self.get_argument('realname')
        # fields['email'] = self.get_argument('email', '')
        fields['expire_date'] = self.get_argument('expire_date')
        fields['mask'] = int(self.get_argument('mask')) | 1

        account.verify_holder(int(holder), **fields)
        self.render_json_response(**OK)

    @_trace_wrapper
    @_parse_body
    def delete(self, holder):
        raise HTTPError(405)
        holder = int(holder)
        _user = account.get_account(holder)
        if _user:
            if not _user['mask']>>1 & 1:
                raise HTTPError(404, 'Not Holder')
            account.remove_holder(holder)

        self.render_json_response(**OK)

class APHandler(AccountBaseHandler):
    '''
        Manage hodler's ap
    '''
    @_trace_wrapper
    def get(self, holder):
        holder = int(holder)
        self.check_holder(holder)
        aps = account.get_aps(int(holder))
        self.render_json_response(Aps=aps, **OK)

    @_trace_wrapper
    @_parse_body
    def post(self, holder):
        holder = int(holder)
        self.check_holder(holder)
        aps = self.get_arguments('aps')
        account.create_aps(holder, aps)
        self.finish('add ap successfully')

    def put(self, holder):
        raise HTTPError(405)

    def delete(self, holder):
        raise HTTPError(405)

class RoomHandler(AccountBaseHandler):
    '''
    '''
    @_trace_wrapper
    # @_parse_body
    def get(self, holder):
        '''
            Get renter's account, contain room field
        '''
        holder = int(holder)
        self.check_holder(holder)
        _user, renters = account.get_renters(holder)
        rooms = [item['room'] for item in renters]
        self.render_json_response(Rooms=rooms, **OK)

    @_trace_wrapper
    @_parse_body
    def post(self, holder):
        '''
            create&add renter's account
            {rooms:[room1, room2]}
        '''
        holder = int(holder)
        self.check_holder(holder)
        rooms = self.get_arguments('rooms')
        rooms = [(room, util.generate_password()) for room in rooms]
        expire_date = self.get_argument('expire_date')
        account.create_renters(holder, expire_date, rooms)
        self.render_json_response(Code=200, Msg='Create room account successfully')

    @_trace_wrapper
    @_parse_body
    def put(self, holder):
        '''
            Update renter account info
            {room:{password:'', expire_date:'', ends:num}}
        '''
        token = self.get_argument('token')
        self.check_token(holder, token)
        holder = int(holder)
        self.check_holder(holder)
        rooms = self.get_argument('rooms')
        logger.info('{}'.format(rooms))
        account.update_renters(holder, rooms)
        self.render_json_response(**OK)
        # self.finish('Update {} info successfully'.format(rooms.keys()))

    @_trace_wrapper
    @_parse_body
    def delete(self, holder):
        token = self.get_argument('token')
        self.check_token(holder, token)
        holder = int(holder)
        room = self.get_argument('room')
        logger.info('{} remove room: {}'.format(holder, room))
        account.remove_holder_room(holder, room)
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
    def udp_hander(fd, events):
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
    trace.init(settings['LOG_BD_PATH'], options.port)
    logger = trace.logger('bidong', False)
    logger.setLevel(logging.INFO)

    bidong_pid = os.path.join(settings['RUN_PATH'], 'p_{}.pid'.format(options.port))
    with open(bidong_pid, 'w') as f:
        f.write('{}'.format(os.getpid()))

    app = Application()
    app.listen(options.port, xheaders=app.settings.get('xheaders', False))
    io_loop = tornado.ioloop.IOLoop.instance()
    logger.info('BIDONG Server Listening:{} Started'.format(options.port))
    io_loop.start()

if __name__ == '__main__':
    main()
