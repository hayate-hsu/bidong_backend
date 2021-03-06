'''
    id = Column('id', INTEGER(),
                primary_key=True, nullable=False, doc='increment id')
    Account manage module
'''
from tornado.web import HTTPError
import datetime
# import math
import collections

from MySQLdb import (IntegrityError)

from db import db
import util

APP_PROFILE = collections.defaultdict(dict)

def get_appid(appid):
    assert appid
    now = datetime.datetime.now()
    if appid in APP_PROFILE and now < APP_PROFILE[appid]['expired']:
        return APP_PROFILE[appid]

    record = db.get_appid(appid)
    if not record:
        raise HTTPError(404, reason='Can\'t found app({}) profile'.format(appid))

    expired = now + datetime.timedelta(days=1)
    record['expired'] = expired
    APP_PROFILE[appid] = record
    return APP_PROFILE[appid]


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
    return db.get_app_version(pt)

def create_version(ver, mask, note):
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
        db.update_app_version(pt, newest=ver, least=ver, note=note)
    else:
        db.add_app_version(pt, ver, note)

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

def create_group(name, note):
    try:
        db.create_group(name, note)
    except IntegrityError:
        raise HTTPError(409, reason='name has been existed')

# def get_manager(user):
def get_manager(user, password=''):
    manager = db.get_manager(user, password)
    # if manager:
    #     manager['password'] = util.md5(manager['password']).hexdigest()
    return manager

@util.check_codes
def create_holder(weixin, mobile, address, realname, portal='login.html', billing=0):
    '''
        portal : authentication page
        billing : billing type
            0 : normal billing type (coin & expire_date)
            1 : free
    '''
    password = util.generate_password()
    now = util.now('%Y-%m-%d %H:%M:%S')

    _id = db.add_holder(weixin, password, mobile, now, 
                        address=address, realname=realname, 
                        portal=portal, billing=billing)
    return _id

def get_holders(page, verified=0):
    '''
        mask = 2  # unverify holder account 
        mask = 3 # verify holder 
    '''
    mask = 2
    if verified:
        mask = 3
    return db.get_holders(page, mask)

@util.check_codes
def verify_holder(holder, **kwargs):
    '''
    '''
    verify = int(kwargs.pop('verify', 0))
    frozen = int(kwargs.pop('frozen', -1))
    db.update_holder(holder, verify, frozen, **kwargs)

def remove_holder(holder):
    db.remove_holder(holder)

def check_ssid(ssid, mac=None):
    return db.check_ssid(ssid, mac)

@util.check_codes
def create_ap(**kwargs):
    '''
        mac
        vendor
        model
        fm
        profile
        position
    '''
    kwargs['mac'] = kwargs['mac'].upper()
    db.add_ap(**kwargs)

@util.check_codes
def update_ap(mac, **kwargs):
    db.update_ap(mac, **kwargs)

def bind_aps(holder, aps):
    '''
    '''
    db.bind_aps(holder, aps)

def unbind_aps(holder, aps):
    '''
    '''
    db.unbind_aps(holder, aps)

def remove_aps(aps):
    '''
    '''
    db.remove_aps(aps)

def get_aps(field, query):
    return db.get_aps(field, query)

def get_holder_by_mac(mac_addr):
    return db.get_holder_by_mac()

def create_renters(holder, expired, rooms):
    '''
        expired : %Y-%m-%d %H:%M:%S
    '''
    db.add_holder_rooms(holder, expired, rooms)

def update_renters(holder, rooms):
    db.update_renters(holder, rooms)

def remove_holder_room(holder, rooms):
    db.remove_holder_room(holder, rooms)

def get_renters(holder):
    bd_account, renters = db.get_holder_renters(holder)    
    holder = str(holder)
    for item in renters:
        item['room'] = item['user'].replace(holder, '')
    return bd_account, renters

def get_account(**kwargs):
    kwargs.pop('mask', 0)
    return db.get_account(**kwargs) or db.get_account2(**kwargs)

def check_account_by_mobile_or_mac(mobile, mac):
    '''
        1. first check mac_history 
         
        2. check user has been register?
               mobile : 
               mac : android register by mac address 
    '''
    _user = db.get_account_by_mobile_or_mac(mobile, mac)
    if not _user:
        # register account by mobile
        password = util.generate_password()
        _user = db.add_user(mobile, password, mobile=mobile, ends=2**8)
        _user['existed'] = 0
        # _user = {'user':user, 'password':password, 'existed':0}
    else:
        if _user['amobile'] != mobile or _user['mobile'] != mobile:
            db.update_account(_user['user'], mobile=mobile)

        _user['existed'] = 1
    return _user

def remove_account(user, mask=1):
    '''
        mask :
            1 : delete account 
            0 : history only
    '''
    if mask:
        db.remove_account(user)
    else:
        db.remove_mac_history(user)

def get_bd_account(user, fields=('user', 'mask', 'ends', 'expired', 'coin')):
    return db.get_bd_user(user) or db.get_bd_user2(user)

def check_weixin_account(appid, openid):
    '''
        check openid existed?
            exist : return
            not exist : create account
    '''
    _user = db.get_account(appid=appid, weixin=openid) or db.get_account2(appid=appid, weixin=openid)

    if not _user:
        # create account
        _user = db.add_user(openid, util.generate_password(), appid=appid, ends=2**5)
    else:
        if _user['amask']>>28 & 1:
            _user['amask'] = _user['amask'] ^ 1<<28
            db.update_account(_user['user'], mask=_user['amask'])

    return _user

def remove_weixin_account(appid, openid):
    _user = db.get_account(appid=appid, weixin=openid) or db.get_account2(appid=appid, weixin=openid)

    if _user:
        _user['amask'] = _user['amask'] | 1<<28
        db.update_account(_user['user'], mask=_user['amask'])

def get_weixin_account(appid, openid):
    account = db.get_account(appid=appid, weixin=openid) or db.get_account2(appid=appid, weixin=openid)

    _user = db.get_bd_user(str(account['id'])) or db.get_bd_user2(str(account['id']))
    return _user

def update_account(user, **kwargs):
    '''
        update user's account info(password...)
        kwargs' key must be bd_account column name
    '''
    if kwargs:
        db.update_user2(user, **kwargs)

def bind(weixin, user):
    '''
        weixin : weixin bd_account
        user : holder's id
    '''
    db.bind(weixin, user)

def unbind(weixin, user):
    db.unbind(weixin, user)

def get_weixin_config():
    return db.get_wx_config()

def get_user_onlines(user, mac):
    return db.get_user_onlines(user, mac)

########################################################
#
#
#   merge app account & mac account
#
#
########################################################
def check_app_account(uuid, mask):
    _user = get_account(uuid=uuid)
    if not _user:
        _user = db.add_user(uuid, util.generate_password(), ends=mask)
    return _user

def merge_account(user, uuid, mask):
    '''
        user : account generage by mac(remove ':')
        uuid : may uuid(ios) or mac(android)
        mask :      1<<7            1<<6
    '''
    _user = check_app_account(uuid, mask)
    # merge account
    merge_app_account(_user['user'], user)
    return _user

def merge_app_account(_id, user):
    '''
        merge app account
        user: account created by mac address
        _id : app account's id
    '''
    db.merge_app_account(_id, user)

#########################################################
#
#
#   coin manager
#
#
##########################################################
def trade(user, coins=0, days=0):
    # trade operate
    # update coin or expire_date
    user = get_bd_account(user)
    if not user:
        raise HTTPError(404, reason='recharge failed, account not existed')
    kwargs = {}
    if coins:
        kwargs['coin'] = user['coin'] + int(coins)
        
    if days:
        expire = ''
        now = datetime.datetime.now()
        # expire_date < now?
        if user['expired'] < now:
            expire = now + datetime.timedelta(days=days)
        else:
            expire = user['expired'] + datetime.timedelta(days=days)
        kwargs['expired'] = expire
    db.update_user2(user, **kwargs)

def untrade(user, billing):
    '''
        un_recharge billing
        reduce user bought coin or days
    '''
    #get billing info
    coin, days = 0, 0
    recharge = db.get_trade(billing)
    if recharge:
       coin = 0 - recharge['coin']
       days = 0 - recharge['days']

    trade(user, coin, days)

def transfer(user, to, coins):
    '''
        user transfer coin to other user
    '''
    # assert transfer to himself & coins > 0
    assert user != to
    assert coins
    # 
    user = get_bd_account(user)
    if not user:
        raise HTTPError(404, reason='recharge failed, account not existed')
    if coins < user['coin']:
        raise HTTPError(403, reason='not enough coins')

    # 
    db.transfer_coin(user, to , coins)

def query_transfer(user):
    '''
        query transfer history
        the lastest 3 months
        coin transfer records
        recharge records
    '''
    # now = datetime.datetime.now()
    # now = now.strftime('%Y-%m-%d')
    db.get_trades(user)

#########################################################
#
#
#   private newtork manager
#
#
##########################################################
def query_avaiable_pns(user, mobile):
    '''
    '''
    return db.query_avaiable_pns(user, mobile)

def bind_avaiable_pns(user, mobile):
    '''
    '''
    return db.bind_avaiable_pns(user, mobile)

def get_pns():
    return db.get_pns()

def create_pn(**kwargs):
    '''
        user create private network with special ssid
    '''
    try:
        db.create_pn(**kwargs)
    except IntegrityError:
        pass

def update_pn(pn, **kwargs):
    '''
        update pn property
    '''
    db.update_pn(pn, **kwargs)

def get_pn_account(holder, **kwargs):
    '''
        holder : identify table (pn_holder)
        kwargs : private network
    '''
    table = 'pn_{}'.format(holder)
    try:
        return db.get_pn_account(table, **kwargs)
    except:
        return None

@util.check_codes
def add_pn_account(holder, **kwargs):
    '''
        private network fields:
            name mobile gender position department ctime mtime
            if operator successfully, return new added id
    '''
    assert 'mobile' in kwargs
    try:
        table = 'pn_{}'.format(holder)
        _id = db.add_pn_account(table, **kwargs)
    except IntegrityError:
        raise HTTPError(403, reason='private network account has been existed, mobile:{}'.format(kwargs['mobile']))
    else:
        return _id

@util.check_codes
def update_pn_account(holder, _id, **kwargs):
    '''
        update existed private network's info
    '''
    try:
        kwargs['mtime'] = util.now()
        table = 'pn_{}'.format(holder)
        db.update_pn_account(table, _id, **kwargs)
    except IntegrityError:
        raise HTTPError(400, reason='mobile number has been existed')

def bind_pn_account(holder, user, mobile):
    '''
        bind bd_account with private network account
    '''
    if not get_pn_account(holder, mobile=mobile):
        return
    user = get_bd_account(user)
    assert user
    
    try:
        db.bind_pn_account(holder, user, mobile)
    except IntegrityError:
        # idx_bind_pairs (user, holder, mobile)
        # duplicate entry
        pass

def unbind_pn_account(holder, mobile):
    '''
    '''
    db.unbind_pn_account(holder, mobile)

def delete_pn_account(holder, mobile):
    '''
    '''
    db.delete_pn_account(holder, mobile)

#########################################################
#
#
#   nansha notice 
# 
#
##########################################################

@util.check_codes
def publish_notice(**kwargs):
    '''
        caption, summary, mask
    '''
    print(kwargs)
    _id = db.publish_notice(**kwargs)
    return _id

@util.check_codes
def update_notice(_id, **kwargs):
    '''
        update caption | summary | mask
    '''
    db.update_notice(_id, **kwargs)

def get_notices(page, mask=0, per=10):
    '''
        page : get the page's detail
        per : record per page
    '''
    start = page*per
    return db.get_notices(start, mask, per)

def remove_notice(_id):
    '''
        delete special notice
    '''
    db.remove_notice(_id)
    # need delete releated resource
    pass

def get_notice(_id):
    '''
        get notice info
    '''
    return db.get_notice(_id)
