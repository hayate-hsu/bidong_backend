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

from tornado.options import define, options

define('port', default=8180, help='running on the given port', type=int)

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

import manage

json_encoder = util.json_encoder
json_decoder = util.json_decoder

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_PATH = settings['cms_path']

# if IMAGE_PATH not existed, mkdir it
IMAGE_PATH = os.path.join(CURRENT_PATH, 'images')
if not os.path.exists(IMAGE_PATH):
    os.mkdir(IMAGE_PATH)
# MOBILE_PATH = os.path.join(TEMPLATE_PATH, 'm')

OK = {'Code':200, 'Msg':'OK'}

_GROUPS_ = {}
# _SECTION_ = {}

class Application(tornado.web.Application):
    '''
        Web application class.
        Redefine __init__ method.
    '''
    def __init__(self):
        handlers = [
            (r'/account', AccountHandler),
            (r'/manager/?(.*)$', ManagerHandler),

            # group interface
            (r'/group/?(.*)$', GroupsHandler),
            # message interface
            (r'/message/section/?(.*)$', SectionHandler),
            (r'/message/?(.*)$', MessageHandler),

            # static resource handler
            (r'/(.*\.(?:css|jpg|png|js|ico|json))$', tornado.web.StaticFileHandler, 
             {'path':TEMPLATE_PATH}),
            (r'/image/?(.*)$', ImageHandler),
            (r'/index.html', MainHandler),
            (r'/(.+\.html)', PageHandler),
            (r'/', MainHandler),
        ]
        settings = {
            'cookie_secret':util.sha1('bidong').hexdigest(), 
            'static_path':TEMPLATE_PATH,
            'static_url_prefix':'images/',
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
                                         module_directory='/tmp/cms/mako',
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

def _check_token(method):
    '''
        check user & token
    '''
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        user = self.get_argument('manager')
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

def _check_groups_(user):
    '''
        If user in _GROUPS_ return it's group values 
        else not in, query 
            if existed, return group
            else:
                raise 404
    '''
    if user in _GROUPS_:
        return _GROUPS_[user]
    # query group info
    manager = manage.get_manager(user)
    if not manager:
        raise HTTPError(404, reason='Can\'t found manager')
    groups = int(manager['groups'])
    _GROUPS_[user] = groups
    return groups

# def _check_section_(value):
#     '''
#         reponse
#     '''
#     value = int(value)
#     if value in _SECTION_:
#         return _SECTION_[value]
# 
#     section = manage.get_section(value)
#     if not section:
#         return 'Unknown'
# 
#     _SECTION_[value] = section['name']
#     return section['name']

class MainHandler(BaseHandler):
    '''
    '''
    @_trace_wrapper
    def get(self):
        manager = self.get_argument('manager', '')
        if manager:
            token = self.get_argument('token')
            token, expired = token.split('|')
            token2 = util.token2(manager, expired)
            if token != token2:
                raise HTTPError(400, reason='Abnormal token')
            self.render('index.html', groups=_check_groups_(manager))
        else:
            self.redirect('login.html')

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

class ManagerHandler(BaseHandler):
    '''
        api/manager/*
        maintain administrator account
    '''
    def _check_admin_(self):
        manager = self.get_argument('manager')
        if _check_groups_(manager) != 1000:
            raise HTTPError(403, reason='Not administrator account')

    @_trace_wrapper
    @_parse_body
    @_check_token
    def get(self, user=''):
        # user = self.get_argument('manager')
        if user:
            manager = manage.get_manager(user)
            if not manager:
                raise HTTPError(404, reason='Can\'t found manager')
        
            self.render_json_response(Code=200, Msg='OK', manager=manager)
        else:
            managers = manage.get_managers()
            self.render_json_response(Code=200, Msg='OK', managers=managers)


        
    @_trace_wrapper
    @_parse_body
    @_check_token
    def post(self, user=''):
        '''
            add new manager account
        '''
        self._check_admin_()
        # user = self.get_argument('manager', '') or self.get_argument('user', '')
        kwargs = {}
        kwargs['user'] = self.get_argument('user')
        kwargs['mask'] = int(self.get_argument('mask', 0))
        kwargs['password'] = self.get_argument('password', '')
        kwargs['groups'] = int(self.get_argument('groups'))
        
        manage.create_manager(**kwargs)
        
        self.render_json_response(Code=200, Msg='OK')

    @_trace_wrapper
    @_parse_body
    @_check_token
    def put(self, user):
        '''
            update manager account
        '''
        self._check_admin_()
        # user = self.get_argument('manager')
        kwargs = {key:value[0] for key,value in self.request.arguments.iteritems()}
        kwargs.pop('token')
        kwargs.pop('manager')

        if 'groups' in kwargs:
            kwargs['groups'] = int(kwargs['groups'])
        manage.update_manager(user, **kwargs)
        self.render_json_response(**OK)

    @_trace_wrapper
    @_parse_body
    @_check_token
    def delete(self, user):
        '''
            delete manager account
        '''
        self._check_admin_()
        # user = self.get_argument('user')
        manage.delete_manager(user)
        self.render_json_response(**OK)

class GroupsHandler(BaseHandler):
    '''
        manager groups
    '''
    @_trace_wrapper
    @_parse_body
    @_check_token
    def get(self, _id=None):
        '''
            get groups or special group details
        '''
        if _id:
            # get special group
            record = manage.get_group(_id)
            return self.render_json_response(Code=200, Msg='OK', group=record)
        else:
            records= manage.get_groups()
            return self.render_json_response(Code=200, Msg='OK', groups=records)

    @_trace_wrapper
    @_parse_body
    @_check_token
    def post(self, _id=None):
        '''
            create new groups
        '''
        name = self.get_argument('name')
        note = self.get_argument('note')
        print(name, note)

        manage.create_group(name, note)

        self.render_json_response(Code=200, Msg='OK') 

class GMTypeHandler(BaseHandler):
    @_trace_wrapper
    @_parse_body
    @_check_token
    def get(self, _id=''):
        manager = self.get_argument('manager')
        group = _check_groups_(manager)
        if _id:
            gmtype = manage.get_gmtype(group, _id)
        else:
            gmtypes = manage.get_gmtypes(group)

    @_trace_wrapper
    @_parse_body
    @_check_token
    def post(self, _id=''):
        manager = self.get_argument('manager')
        group = _check_groups_(manager)
        name = self.get_argument('name')
        manage.create_gmtype(group, name)
        self.render_json_response(**OK)

    @_trace_wrapper
    @_parse_body
    @_check_token
    def delete(self, _id=''):
        manager = self.get_argument('manager')
        group = _check_groups_(manager)
        manage.delete_gmtype(group, _id)
        self.render_json_response(**OK)

class AccountHandler(BaseHandler):
    '''
        manager account login
    '''
    __ADMIN__ = 1000

    @_trace_wrapper
    @_parse_body
    # @_check_token
    def post(self):
        '''
            manager login
        '''
        user = self.get_argument('manager')
        password = self.get_argument('password')

        _user = manage.get_manager(user)
        print(user, _user)
        if not _user:
            raise HTTPError(404, reason='can\'t found account')
        if password != _user['password']:
            raise HTTPError(403, reason='password error')

        token = util.token(user)

        _user.pop('possword', '')

        if _user['groups'] == self.__ADMIN__:
            # admin account, response page contains group manager 
            pass
        else:
            # only message manager contents
            pass

        self.render_json_response(User=_user['user'], token=token, **OK)
        logger.info('Manager: {} login successfully'.format(user))
        #
        # self.render('cms_platform.html', token=token, **_user)

# **************************************************
#
#  Message handler
#
# **************************************************
class SectionHandler(BaseHandler):
    '''
        manager message type
    '''
    @_trace_wrapper
    def get(self, _id=''):
        if _id:
            record = manage.get_section(_id)
            self.render_json_response(Code=200, Msg='OK', section=record)
        else:
            records = manage.get_sections()
            self.render_json_response(Code=200, Msg='OK', sections=records)

    @_trace_wrapper
    @_parse_body
    @_check_token
    def post(self, _id=''):
        '''
            add new message type
        '''
        name = self.get_argument('name')
        manage.add_section(name)

        self.render_json_response(**OK)

    @_trace_wrapper
    @_parse_body
    @_check_token
    def delete(self, _id):
        '''
            delete special message type by id
        '''
        manage.delete_section(_id)
        self.render_json_response(**OK)

class MessageHandler(BaseHandler):
    '''
        maintain message
        message type: 
            news
            notices (use subtitle)
            push to app notices (use subtitle)
            recruit
    '''
    def render_message_response(self, message):
        '''
            return html|json based on the Accept contents
        '''
        accept = self.request.headers.get('Accept', 'text/html')
        if accept.startswith('application/json'):
            self.render_json_response(Code=200, Msg='OK', **message)
        else:
            self.render('message.tmpt', **message)

    @_trace_wrapper
    @_parse_body
    #@_check_token
    def get(self, _id=''):
        '''
            get message
        '''
        if _id:
            message = manage.get_message(_id)
            if not message:
                raise HTTPError(404, reason='Can\'t found message')
            return self.render_message_response(message)

        # get messages 
        manager = self.get_argument('manager', '')
        groups = 0
        if manager:
            # manager get it's messages
            token = self.get_argument('token')
            token, expired = token.split('|')
            token2 = util.token2(manager, expired)
            if token != token2:
                raise HTTPError(400, reason='Abnormal token')
            groups = _check_groups_(manager)
        else:
            # user get messages
            groups = int(self.get_argument('groups'))
        page = int(self.get_argument('page', 0))
        nums = int(self.get_argument('per', 10))
        mask = int(self.get_argument('mask', 0))
        gmtype = int(self.get_argument('gmtype', 0))
        pos = page*nums

        messages = manage.get_messages(groups, mask, gmtype, pos, nums)
        isEnd = 1 if len(messages) < nums else 0

        self.render_json_response(Code=200, Msg='OK', messages=messages, end=isEnd)

    @_trace_wrapper
    @_parse_body
    @_check_token
    def post(self, _id=''):
        '''
            create new message record
            title subtitle section mask author groups status ctime content image
        '''
        logger.info('{}'.format(self.request.arguments))
        manager = self.get_argument('manager')
        kwargs = {key:value[0] for key,value in self.request.arguments.iteritems()}
        kwargs['author'] = manager
        kwargs.pop('token')
        kwargs.pop('manager')
        kwargs['groups'] = _check_groups_(manager)
       
        manage.create_message(**kwargs)
        self.render_json_response(**OK)

    @_trace_wrapper
    @_parse_body
    @_check_token
    def put(self, _id):
        '''
            update message record
        '''
        kwargs = {key:value[0] for key,value in self.request.arguments.iteritems()}
        kwargs.pop('token')
        kwargs.pop('manager')

        manage.update_message(_id, **kwargs)
        self.render_json_response(**OK)

    @_trace_wrapper
    @_parse_body
    @_check_token
    def delete(self, _id):
        manage.delete_message(_id)
        self.render_json_response(**OK)

# @tornado.web.stream_request_body
class ImageHandler(BaseHandler):
    '''
        1. user upload image & update databse
    '''
    # def initialize(self):
    #     self.bytes_read = 0

    # def data_received(self, data):
    #     self.bytes_read += len(data)

    def _gen_image_id_(self, *args):
        now = util.now()

        return util.md5(now, *args).hexdigest()

    @_trace_wrapper
    def get(self, _id):
        filepath = os.path.join(IMAGE_PATH, _id)
        with open(filepath, 'rb') as f:
            data = f.read()
        # self.set_header('Content-Type', record['ext'])
            self.finish(data)

    @_trace_wrapper
    # @_parse_body
    def post(self, _id=None):
        '''
            engineer uplaod image
            update engineer's image
        '''
        # engineer = self.get_argument('engineer')
        file_metas = self.request.files['uploadImg']
        filename = _id
        for meta in file_metas:
            filename = meta['filename']
            if not _id:
                filename = self._gen_image_id_(filename, util.generate_password(8)) 
            else:
                filename = _id
            filepath = os.path.join(IMAGE_PATH, filename)
            with open(filepath, 'wb') as uf:
                uf.write(meta['body'])
            break

        if filename:
            self.render_json_response(name=filename, **OK)
        else:
            raise HTTPError(400)
    
#***************************************************
#
#   
#     Nansha city handler
#
#
#****************************************************
class NSNoticeHandler(BaseHandler):
    '''
        App get notices
        Manager add new record 
    '''
    PER = 10

    def check_token(self, user, token):
        token, expired = token.split('|')
        token2 = util.token2(user, expired)
        if token != token2:
            raise HTTPError(400, reason='abnormal token')

    @_trace_wrapper
    @_parse_body
    def get(self, _id=''):
        '''
            get notices & special notice
        '''
        accept = self.request.headers.get('Accept', 'text/html')
        if _id:
            # get special notice
            notice = account.get_notice(_id)
            if not notice:
                raise HTTPError(404, reason='Can\'t found notice:{}'.format(_id))
            if accept.startswith('application/json'):
                return self.render_json_response(Code=200, Msg='OK', **notice)
            else:
                return self.render('nansha/{}.html'.format(_id), **notice)
        else:
            # get notices
            # item: id, datetime, caption, 
            page = self.get_argument('page', 0)
            notices = account.get_notices(page)
            isEnd = 0
            if len(notices) < self.PER:
                isEnd = 1
            return self.render_json_response(notices=notices, isEnd=isEnd, **OK)

    @_trace_wrapper
    @_parse_body
    def post(self, _id=None):
        '''
            add new notice
        '''
        m_token = self.get_argument('token')
        manager = self.get_argument('manager')
        self.check_token(manager, m_token)

        caption = self.get_argument('caption')
        summary = self.get_argument('summary')
        mask = int(self.get_argument('mask', 0))

        _id = account.publish_notice(caption=caption, summary=summary, mask=mask)

        logger.info('publish new notice: id:{}, mask:{}'.format(_id, mask))

        self.render_json_response(id=_id, **OK)

    @_trace_wrapper
    @_parse_body
    def put(self, _id):
        '''
            update existed notice
        '''
        m_token = self.get_argument('token')
        manager = self.get_argument('manager')
        self.check_token(manager, m_token)

        kwargs = {key:value[0] for key,value in self.request.arguments.iteritems()}
        kwargs.pop('token')
        kwargs.pop('manager')

        account.update_notice(_id, **kwargs)

        self.render_json_response(id=_id, **OK)

    @_trace_wrapper
    @_parse_body
    def delete(self, _id):
        '''
            update existed notice
        '''
        m_token = self.get_argument('token')
        manager = self.get_argument('manager')
        self.check_token(manager, m_token)

        account.remove_notice(_id)

        self.render_json_response(id=_id, **OK)

class NSAccountHandler(BaseHandler):
    '''
        manager edit employee's details
    '''
    def check_token(self, user, token):
        token, expired = token.split('|')
        token2 = util.token2(user, expired)
        if token != token2:
            raise HTTPError(400, reason='abnormal token')

    @_trace_wrapper
    @_parse_body
    def get(self, employee=None):
        '''
            return special employee
            can be searched by id & mobile
        '''
        kwargs = {}
        if employee:
            kwargs['id'] = employee
        else:
            kwargs['mobile'] = self.get_argument('mobile')
        if not kwargs:
            raise HTTPError(400)
        record = account.get_ns_employee(**kwargs)
        if not record:
            raise HTTPError(404)

        self.render_json_response(Code=200, Msg='OK', **record)


    @_trace_wrapper
    @_parse_body
    def post(self, employee=None):
        '''
            manager add new employee records
        '''
        token = self.get_argument('token')
        manager = self.get_argument('manager')
        self.check_token(manager, token)

        kwargs = {key:value[0] for key,value in self.request.arguments.iteritems()}
        kwargs.pop('token')
        kwargs.pop('manager')
        # kwargs = {}
        # kwargs['user'] = self.get_argument('user')
        # kwargs['name'] = self.get_argument('name')
        # kwargs['gender'] = int(self.get_argument('gender', 0))
        # kwargs['mobile'] = self.get_argument('mobile')
        # kwargs['position'] = self.get_argument('position', '')
        # kwargs['department'] = self.get_argument('department', '')

        _id = account.add_ns_employee(**kwargs)
        
        logger.info('add new employee successfully(id:{}, mobile:{})'.format(_id, kwargs['mobile']))
        self.render_json_response(id=_id, **OK)

    @_trace_wrapper
    @_parse_body
    def put(self, employee):
        '''
            update employee's info
        '''
        token = self.get_argument('token')
        manager = self.get_argument('manager')
        self.check_token(manager, token)

        kwargs = {key:value[0] for key,value in self.request.arguments.iteritems()}
        kwargs.pop('token')
        kwargs.pop('manager')

        if kwargs:
            account.update_ns_employee(employee, **kwargs)

        logger.info('update {}\'s info: {}'.format(employee, kwargs))

        self.render_json_response(**OK)

    @_trace_wrapper
    @_parse_body
    def delete(self, employee):
        '''
            delete special employee by mobile
        '''
        token = self.get_argument('token')
        manager = self.get_argument('manager')
        self.check_token(manager, token)

        mobile = self.get_argument('mobile')

        account.delete_ns_employee(mobile) 

        logger.info('delete employee : (id:{}, mobile:{})'.format(employee, mobile))

        self.render_json_response(**OK)

class NSBindHandler(BaseHandler):
    '''
        bind nansha employee's mobile with bd_account
    '''
    def check_token(self, user, token):
        token, expired = token.split('|')
        token2 = util.token2(user, expired)
        if token != token2:
            raise HTTPError(400, reason='abnormal token')

    @_trace_wrapper
    @_parse_body
    def post(self):
        token = self.get_argument('token')
        user = self.get_argument('user')
        self.check_token(user, token)

        token, expired = token.split('|')
        token2 = util.token2(user, expired)
        if token != token2:
            raise HTTPError(400, reason='abnormal token')

        mobile = self.get_argument('mobile')

        account.bind_ns_employee(mobile, user)

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
    trace.init(settings['LOG_CMS_PATH'], options.port)
    logger = trace.logger('cms', False)
    logger.setLevel(logging.INFO)

    bidong_pid = os.path.join(settings['CMS_RUN_PATH'], 'p_{}.pid'.format(options.port))
    with open(bidong_pid, 'w') as f:
        f.write('{}'.format(os.getpid()))

    app = Application()
    app.listen(options.port, xheaders=app.settings.get('xheaders', False))
    io_loop = tornado.ioloop.IOLoop.instance()
    logger.info('CMS Server Listening:{} Started'.format(options.port))
    io_loop.start()

if __name__ == '__main__':
    main()
