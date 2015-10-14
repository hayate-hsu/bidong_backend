'''
    id = Column('id', INTEGER(),
                primary_key=True, nullable=False, doc='increment id')
    Account manage module
'''
from tornado.web import HTTPError
import datetime
import math

from MySQLdb import (IntegrityError)

from db import db
import util

# ****************************************
# 
#  version operator
#
# ****************************************
def check_version(ver, mask):
    '''
        return: the newest version, the least avaiable version
    '''
    ver = [int(item) for item in ver.split('.')]
    pt = ''
    if mask>>6 & 1:
        pt = 'Android'
    elif mask>>7 & 1:
        pt = 'IOS'
    else:
        raise HTTPError(400, reason='Unknown platform')
    record = db.get_app_version(pt)
    least = [int(item) for item in record['least'].split('.')]
    newest = [int(item) for item in record['newest'].split('.')]
    return ver==newest, ver>=least

def update_version(mask, **kwargs):
    pt = ''
    if mask>>6 & 1:
        pt = 'Android'
    elif mask>>7 & 1:
        pt = 'IOS'
    else:
        raise HTTPError(400, reason='Unknown platform')
    db.update_app_version(pt, **kwargs)

def get_version(mask):
    pt = ''
    if mask>>6 & 1:
        pt = 'Android'
    elif mask>>7 & 1:
        pt = 'IOS'
    else:
        raise HTTPError(400, reason='Unknown platform')
    db.get_app_version(pt)

def create_version(ver, mask):
    '''
        create app version
    '''
    pt = ''
    if mask>>6 & 1:
        pt = 'Android'
    elif mask>>7 & 1:
        pt = 'IOS'
    else:
        raise HTTPError(400, reason='Unknown platform')
    record = get_version(mask)
    if record:
        db.update_app_version(pt, newest=ver, least=ver)
    else:
        db.add_app_version(pt, ver)


# ****************************************
# 
#  group operator
#
# ****************************************
def get_group(_id):
    return db.get_group(_id)

def get_groups():
    '''
        sorted by id
    '''
    return db.get_groups()

@util.check_codes
def create_group(name, note):
    try:
        db.create_group(name, note)
    except IntegrityError:
        raise HTTPError(409, reason='name has been existed')

@util.check_codes
def create_gmtype(group, _type):
    try:
        db.create_gmtype(group, _type)
    except IntegrityError:
        raise HTTPError(409, reason='name has been existed')

def get_gmtype(group, _id):
    return db.get_gmtype(group, _id)

def get_gmtypes(group):
    return db.get_gmtypes(group)

def delete_gmtype(group, _id):
    delete_gmtype(group, _id)

# **************************************
#
# manager operator
#
# **************************************
def create_manager(**kwargs):
    if not kwargs['password']:
        kwargs['password'] = util.generate_password(len=6)
    
    try:
        db.create_manager(**kwargs)
    except IntegrityError:
        raise HTTPError(409, reason='duplicate account')

def update_manager(user, **kwargs):
    if kwargs:
        db.update_manager(user, **kwargs)

def delete_manager(user):
    db.delete_manager(user)

def get_manager(user):
    manager = db.get_manager(user)
    # if manager:
    #     manager['password'] = util.md5(manager['password']).hexdigest()
    return manager

def get_managers():
    pass


# **************************************
#
# message operator
#
# **************************************
@util.check_codes
def add_section(name):
    try:
        db.add_section(name)
    except IntegrityError:
        raise HTTPError(409, reason='duplicate message type')

def delete_section(_id):
    db.delete_section(_id)

def get_section(_id):
    return db.get_section(_id)

def get_sections():
    return db.get_sections()

@util.check_codes
def create_message(**kwargs):
    # generate message's unique id (author, title, subtitle, content)
    code = util.md5(kwargs['author'], kwargs['title'], kwargs['subtitle'], kwargs['content']) 
    code = code.hexdigest()
    kwargs['id'] = code
    try:
        db.create_message(**kwargs)
    except IntegrityError:
        raise HTTPError(409, reason='duplicate message')

@util.check_codes
def update_message(_id, **kwargs):
    db.update_message(_id, **kwargs)

def delete_message(_id):
    db.delete_message(_id)

def get_message(_id):
    return db.get_message(_id)

def get_messages(groups, mask, isimg, gmtype, pos, nums):
    '''
        get messages 
        filter  : groups, mask
        position: start , per
    '''
    return db.get_messages(groups, mask, isimg, gmtype, pos, nums)
