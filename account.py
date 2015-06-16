'''
    id = Column('id', INTEGER(),
                primary_key=True, nullable=False, doc='increment id')
    Account manage module
'''
from tornado.web import HTTPError

from db import db
import util

def get_manager(user):
    return db.get_manager(user)

@util.check_codes
def create_holder(weixin, mobile, address, realname, email):
    '''
    '''
    password = util.generate_password()
    # now = util.now('%Y-%m-%d')
    _id = db.add_holder(weixin, password, mobile, '', 
                        address=address, realname=realname)
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

def verify_holder(holder, **kwargs):
    '''
    '''
    verify = int(kwargs.pop('verify', 0))
    frozen = int(kwargs.pop('frozen', -1))
    db.update_holder(holder, verify, frozen, **kwargs)

def remove_holder(holder):
    db.remove_holder(holder)

def create_aps(aps):
    '''
    '''
    db.add_aps(aps)

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

def get_aps(holder=None, mac=None):
    return db.get_aps(holder, mac)

def get_holder_by_mac(mac_addr):
    return db.get_holder_by_mac()

def create_renters(holder, expire_date, rooms):
    db.add_holder_rooms(holder, expire_date, rooms)

def update_renters(holder, rooms):
    db.update_renters(holder, rooms)

def remove_holder_room(holder, rooms):
    db.remove_holder_room(holder, rooms)

def get_renters(holder):
    account = get_account(holder) 
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

def get_account(id):
    account = db.get_user_by_id(id)
    # mask = account['mask']
    # if not (mask>>1 & 1):
    #     raise HTTPError(404, 'Not holder') 
    return account

def get_account_by_openid(openid):
    return db.get_user(openid)

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

def bind(weixin, user):
    '''
        weixin : weixin bd_account
        user : holder's id
    '''
    db.bind(weixin, user)

