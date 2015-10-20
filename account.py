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

def create_group(name, note):
    try:
        db.create_group(name, note)
    except IntegrityError:
        raise HTTPError(409, reason='name has been existed')

def get_manager(user):
    return db.get_manager(user)

def registe(mac, mask):
    # check user has been registed?
    _id = ''
    account = db.get_user(mac, mask)
    if not account:
        # check mac address login history
        # create account
        account = db.get_user_by_mac(mac)
        if not account:
            _id = db.add_user(mac, util.generate_password(), mask)

    return _id or account['id']

@util.check_codes
def create_holder(weixin, mobile, address, realname, portal='login.html', billing=0):
    '''
        portal : authentication page
        billing : billing type
            0 : normal billing type (coin & expire_date)
            1 : free
    '''
    password = util.generate_password()
    # now = util.now('%Y-%m-%d')
    _id = db.add_holder(weixin, password, mobile, '', 
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

def create_renters(holder, expire_date, rooms):
    db.add_holder_rooms(holder, expire_date, rooms)

def update_renters(holder, rooms):
    db.update_renters(holder, rooms)

def remove_holder_room(holder, rooms):
    db.remove_holder_room(holder, rooms)

def get_renters(holder):
    account = get_account(id=holder) 
    results = db.get_holder_renters(holder)    
    bd_account, renters = {}, []
    for item in results:
        if int(item['user']) == holder:
            bd_account = item
            continue
        item['room'] = item['user'].replace(str(holder), '')
        if item['room']:
            renters.append(item)
    print(account, bd_account)
    bd_account['realname'] = account['realname']
    bd_account['address'] = account['address']
    bd_account['mobile'] = account['mobile']
    return bd_account, renters

# def get_account(id, mask):
#     account = db.get_user_by_id(id)
#     return account

def get_account(**kwargs):
    return db.get_account(**kwargs)

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

def get_bd_account(user, fields=('user', 'mask', 'ends', 'expire_date', 'time_length', 'coin')):
    account = db.get_bd_user(user)
    return account

def create_weixin_account(openid):
    '''
        check openid existed?
            exist : return
            not exist : create account
    '''
    account = db.get_user(openid)
    if not account:
        # create account
        db.add_user(openid, util.generate_password())
    else:
        if account['mask']>>28 & 1:
            account['mask'] = account['mask'] ^ 1<<28
            db.update_user(openid, account)

def remove_weixin_account(openid):
    account = db.get_user(openid)
    if account:
        account['mask'] = account['mask'] | 1<<28
        db.update_user(openid, account)

def get_weixin_account(openid):
    account = db.get_user(openid)
    _user = db.get_bd_user(str(account['id']))
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

########################################################
#
#
#   merge app account & mac account
#
#
########################################################
def create_app_account(uuid, mask):
    _id = db.add_user(uuid, util.generate_password(), mask)
    return _id

def merge_account(user, uuid, mask):
    '''
        user : account generage by mac(remove ':')
        uuid : may uuid(ios) or mac(android)
        mask :      1<<7            1<<6
    '''
    _id = ''
    _account = get_account(uuid=uuid)
    if not _account:
        # create new account
        _id = create_app_account(uuid, mask)
    else:
        _id = _account['id']

    # merge account
    merge_app_account(_id, user)
    return _id

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
        now.replace()
        if not user['expire_date']:
            expire = now + datetime.timedelta(days=days)
        else:
            # expire_date < now?
            old_expire = datetime.strptime('%Y-%d-%m %H:%M:%S', user['expire_date'] + ' 23:59:59')
            if old_expire < now:
                expire = now + datetime.timedelta(days=days)
            else:
                expire = old_expire + datetime.timedelta(days=days)
        kwargs['expire_date'] = expire.strftime('%Y-%d-%m')
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
#   nansha employee manager
#
#
##########################################################
def get_ns_employee(**kwargs):
    '''
        kwargs: nan sha employee fields
    '''
    return db.get_ns_employee(**kwargs)

def get_ns_employees(pos, nums):
    pass

@util.check_codes
def add_ns_employee(**kwargs):
    '''
        employee table fields:
            name mobile gender position department ctime mtime
            if operator successfully, return new added id
    '''
    assert 'mobile' in kwargs
    # employee = get_ns_employee(mobile=kwargs['mobile'])
    # if employee:
    #     raise HTTPError(400, reason='employee has been existed')
    try:
        _id = db.add_ns_employee(**kwargs)
    except IntegrityError:
        raise HTTPError(403, reason='employee has been existed, mobile:{}'.format(kwargs['mobile']))
    else:
        return _id

@util.check_codes
def update_ns_employee(_id, **kwargs):
    '''
        update existed employee's info
    '''
    try:
        kwargs['mtime'] = util.now()
        db.update_ns_employee(_id, **kwargs)
    except IntegrityError:
        raise HTTPError(400, reason='mobile number has been existed')

def get_binded_account(mobile):
    '''
    '''
    return db.get_employee_binded_account(mobile)

def bind_ns_employee(mobile, user):
    '''
        mobile : mobile number
        user : bd_account 
    '''
    if not get_ns_employee(mobile=mobile):
        return
    user = get_bd_account(user)
    assert user
    # user record 
    db.bind_ns_employee(mobile, user)

def delete_ns_employee(mobile):
    db.delete_ns_employee(mobile)

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
