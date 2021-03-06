#!/usr/bin/env python
#coding=utf-8
# from DBUtils.PooledDB import PooledDB
from DBUtils.PersistentDB import PersistentDB
# from beaker.cache import CacheManager
# import functools
# import settings
import datetime
try:
    import MySQLdb
except:
    pass

import settings
import util

__cache_timeout__ = 600

# 0b 01111111 11111111 11111111 11111111
__MASK__ = 2147483647

# cache = CacheManager(cache_regions= {'short_term':{'type':'memory', 
#                                                    'expire':__cache_timeout__}})

ticket_fds = [
    'user', 'acct_input_octets', 'acct_output_octets', 'acct_input_packets', 'acct_output_packets', 
    'acct_session_id', 'acct_session_time', 'acct_start_time', 'acct_stop_time', 
    'acct_terminate_cause', 'frame_netmask', 'framed_ipaddr', 'is_deduct', 'nas_addr',
    'session_timeout', 'start_source', 'stop_source', 'mac_addr'
]

class Connect:
    def __init__(self, dbpool):
        self.conn = dbpool.connect()

    def __enter__(self):
        self.conn.begin()
        return self.conn

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.conn.close()

class Cursor:
    def __init__(self, dbpool):
        self.conn = dbpool.connect()
        self.cursor = dbpool.cursor(self.conn)

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.conn.close()

class MySQLPool():
    def __init__(self, config):
        self.dbpool = PersistentDB(
            creator=MySQLdb,
            db=config['db'],
            host=config['host'],
            port=config['port'],
            user=config['user'],
            passwd=config['passwd'],
            charset=config['charset'],
            maxusage=config['maxusage'],

            # set read & write timeout
            read_timeout=config['read_timeout'],
            write_timeout=config['write_timeout'],
        )

    def cursor(self, conn):
        return conn.cursor(MySQLdb.cursors.DictCursor)

    def connect(self):
        return self.dbpool.connection()

pool_class = {'mysql':MySQLPool}

class Store():
    def setup(self, config):
        self.dbpool = MySQLPool(config['database'])
        # global __cache_timeout__
        # __cache_timeout__ = config['cache_timeout']

    def _combine_query_kwargs(self, **kwargs):
        '''
            convert query kwargs to str
        '''
        query_list = []
        for key,value in kwargs.iteritems():
            if isinstance(value, int):
                query_list.append('{}={}'.format(key, value))
            else:
                query_list.append('{}="{}"'.format(key, value))
        return 'and '.join(query_list)

    # ************************************************
    #
    # app version operator
    #
    # ************************************************ 
    def add_app_version(self, pt, version, note):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'insert into app_ver (pt, newest, least, note) values("{}", "{}", "{}", "{}")'.format(pt, version, version, note)
            cur.execute(sql)
            conn.commit()

    def update_app_version(self, pt, **kwargs):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            modify_str = ', '.join('{} = "{}"'.format(key, value) for key,value in kwargs.iteritems())
            sql = 'update app_ver set {} where pt = {}'.format(modify_str, pt)
            cur.execute(sql)
            conn.commit()

    def get_app_version(self, pt):
        with Cursor(self.dbpool) as cur:
            cur.execute('select * from app_ver where pt="{}"'.format(pt))
            return cur.fetchone()

    def get_appid(self, appid):
        with Cursor(self.dbpool) as cur:
            cur.execute('select * from app where appid="{}"'.format(appid))
            return cur.fetchone()

    # *********************************************
    #
    # message operator
    #
    # *********************************************
    def list_bas(self):
        '''
            Get ac lists
        '''
        with Cursor(self.dbpool) as cur:
            cur.execute('select * from bas')
            return list(cur)
            # return [bas for bas in cur]

    def get_bas(self, ip):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            cur.execute('select * from bas where ip = "{}"'.format(ip))
            bas = cur.fetchone()
            return bas

    def get_account(self, **kwargs):
        '''
            get account's info
        '''
        with Cursor(self.dbpool) as cur:
            mask = kwargs.pop('mask', 0)
            query_str = self._combine_query_kwargs(**kwargs)
            if mask:
                pass
            else:
                sql = '''select bd_account.*, account.mask as amask, account.realname, account.address
                from bd_account 
                left join account on bd_account.user=cast(account.id as char)  
                where {}'''.format(query_str)
            cur.execute(sql)
            return cur.fetchone()

    def get_account2(self, **kwargs):
        with Connect(self.dbpool) as conn:
            conn.commit()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            query_str = self._combine_query_kwargs(**kwargs)
            sql = '''select bd_account.*, account.mask as amask, account.realname, account.address
            from bd_account 
            left join account on bd_account.user=cast(account.id as char) 
            where {}'''.format(query_str)
            cur.execute(sql)
            return cur.fetchone()

    def get_account_by_uuid(self, uuid, mask):
        with Cursor(self.dbpool) as cur:
            # search account by uuid
            sql = '''select bd_account.*, account.uuid from bd_account 
            left join account on bd_account.user=cast(account.id as char) 
            where account.uuid="{}"'''.format(uuid)
            cur.execute(sql)
            result = cur.fetchone()
            if result:
                return result

            if mask and mask>>6&1:
                sql = '''select bd_account.*, account.uuid from bd_account 
                left join mac_history on bd_account.user=mac_history.user
                left join account on bd_account.user=cast(account.id as char)
                where mac_history.mac="{}" order by account.ctime'''.format(uuid)
                cur.execute(sql)
                return cur.fetchone()
            return None

    def get_account_by_mobile_or_mac(self, mobile, mac):
        with Cursor(self.dbpool) as cur:
            # search account by mobile
            if mobile:
                sql = '''select bd_account.*, account.mobile as amobile from bd_account 
                left join account on bd_account.user=cast(account.id as char)  
                where account.mobile="{}"'''.format(mobile)
                cur.execute(sql)

                result = cur.fetchone()
                if result:
                    return result
            
            # search account by mac_history
            if mac:
                sql = '''select bd_account.*, account.mobile as amobile from bd_account 
                left join mac_history on bd_account.user=mac_history.user 
                left join account on bd_account.user=cast(account.id as char) 
                where mac_history.mac="{}" order by account.ctime'''.format(mac)
                cur.execute(sql)
                return cur.fetchone()

            return None

    def update_account(self, user, **kwargs):
        '''
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            if kwargs:
                modify_str = ', '.join(['{} = "{}"'.format(key, value) for key,value in kwargs.iteritems()])
                sql = 'update account set {} where id = {}'.format(modify_str, user) 
                cur.execute(sql)

                mobile = kwargs.get('mobile', '')
                if mobile:
                    sql = 'update bd_account set mobile={} where user="{}"'.format(mobile, user)
                    cur.execute(sql)

                conn.commit()


    def add_holder(self, weixin, password, mobile, expired,
                      email='', address='', realname='', billing=0):
        '''
            add hold user, user must with tel & address
            mask = 0 + 2**1 + [2**8]
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            user = []
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if weixin:
                # account has been existed
                sql = 'select id, mask from account where weixin = "{}"'.format(weixin)
                cur.execute(sql)
                user = cur.fetchone()
                mask = user['mask'] + 2**1
                sql = '''update account set mask = {}, mobile = "{}", 
                email="{}", address="{}", realname="{}" where id = {}
                '''.format(mask, mobile, email, address, realname, user['id'])
                cur.execute(sql)
            else:
                mask = 0 + 2**1
                sql = '''insert into account 
                (mobile, email, mask, address, 
                realname, ctime, expired) 
                values("{}", "{}", {}, "{}", "{}", "{}", "{}")
                '''.format(mobile, email, mask, address, 
                           realname, now, expired)
                cur.execute(sql)
                sql = 'select id from account where mobile = "{}"'.format(mobile)
                cur.execute(sql)
                user = cur.fetchone()

                mask = mask + 2**8 + 2**3

                sql = '''insert into bd_account (user, password, mask, expired, coin, holder, ends) 
                values("{}", "{}", {}, "{}", 0, {}, 2)
                '''.format(str(user['id']), password, mask, expired, user['id'])
                cur.execute(sql)

            conn.commit()
            return user['id']

    def get_holders(self, page, mask):
        with Cursor(self.dbpool) as cur:
            # each time get max 20 item records
            per = 10
            pages = 0
            results = []
            if page == 0:
                sql = 'select count(id) as counts from account where mask & 3 = {}'.format(mask)
                cur.execute(sql)
                pages = cur.fetchone()['counts']
            start = page*per
            sql = '''select id, realname, mobile, mask, address, expired from account where mask & 3 = {} order by id desc limit {}, {}'''.format(mask, start, per)
            cur.execute(sql)
            results = cur.fetchall()
            results = results if results else []
            return int((pages+per-1)/per), results

    def update_holder(self, holder, verify, frozen, **kwargs):
        '''
            update holder info
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            print('kwargs:', kwargs)
            if kwargs:
                modify_str = ', '.join('{} = "{}"'.format(key, value) for key,value in kwargs.iteritems())
                sql = 'update account set {} where id = {}'.format(modify_str, holder)
                print(sql)
                cur.execute(sql)

            cur.execute('select mask from bd_account where user = "{}"'.format(holder))
            _user = cur.fetchone()

            # update bd_account
            modify_dict = {}
            mask = kwargs.get('mask', 0)
            if verify:
                modify_dict['mask'] = _user['mask'] | 1 | (1<<3) 
                modify_dict['holder'] = holder
            elif frozen == 1 and mask and mask & 1<<30:
                modify_dict['mask'] = _user['mask'] | 1<<30
            elif frozen == 0 and mask and not (mask & 1<<30):
                # account unforzen
                modify_dict['mask'] = (_user['mask'] ^ 1<<30) if (_user['mask'] & 1<<30) else _user['mask']

            if 'expired' in kwargs:
                modify_dict['expired'] = kwargs['expired']

            if modify_dict:
                modify_str = ', '.join('{} = "{}"'.format(key,value) for key,value in modify_dict.iteritems())
                sql = 'update bd_account set {} where user = "{}"'.format(modify_str, holder)
                cur.execute(sql)

            # update renters account
            if frozen == 1 and mask and (mask & 1<<30):
                sql = 'select user, mask from bd_account where holder = {} and user <> "{}"'.format(holder, holder)
                cur.execute(sql)
                renters = cur.fetchall()
                for renter in renters:
                    sql = 'update bd_account set mask = {} where user = "{}"'.format(renter['mask'] & 1<<30, renter['user'])
                    cur.execute(sql)
            elif frozen == 0 and mask and not (mask & 1<<30):
                sql = 'select user, mask from bd_account where holder = {} and mask & 1<<30'.format(holder)
                cur.execute(sql)
                renters = cur.fetchall()
                for renter in renters:
                    sql = 'update bd_account set mask = {} where user = "{}"'.format(renter['mask'] ^ 1<<30, renter['user'])
                    cur.execute(sql)

            conn.commit()

    def remove_holder(self, holder):
        '''
            remove hodler & hoder's renters
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            # delete binded macs
            sql = 'delete from holder_ap where holder = "{}"'.format(holder)
            cur.execute(sql)
            # remove renters
            sql = 'delete from bd_account where holder = "{}"'.format(holder)
            cur.execute(sql)
            # remove account
            sql = 'delete from account where id = "{}"'.format(holder)
            cur.execute(sql)
            conn.commit()

    def check_ssid(self, ssid, mac):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            mac = mac[:]
            sql = 'select * from holder_ap where mac like "{}%"'.format(mac[:-2])
            cur.execute(sql)
            record = cur.fetchone()
            if not record:
                return 0, None
            # query pn_policy
            sql = 'select * from pn_policy where pn={} and ssid="{}"'.format(record['holder'], ssid)
            cur.execute(sql)
            record = cur.fetchone()
            if not record:
                # can\'t found pn and ssid
                return 1, None
                # issys ispri
            return 1, record


    def add_ap(self, **kwargs):
        '''
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            key_str = ', '.join(kwargs.keys())
            value_str = ', '.join(['"%s"'%c for c in kwargs.values()])
            sql = 'insert into aps ({}) values({})'.format(key_str, value_str)
            cur.execute(sql)
            conn.commit()

    def update_ap(self, mac, **kwargs):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            modify_str = ', '.join('{} = "{}"'.format(key,value) for key,value in kwargs.iteritems())
            sql = 'update aps set {} where mac = "{}"'.format(modify_str, mac)
            cur.execute(sql)
            conn.commit()
            

    def get_aps(self, field, query):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            sql = ''
            if field == 'holder':
                sql = '''select aps.*, holder_ap.holder from aps, holder_ap 
                where holder_ap.holder = {} and holder_ap.mac = aps.mac group by aps.mac'''.format(query)
            else:
                sql = 'select * from aps where mac = "{}"'.format(query)
            cur.execute(sql)

            results = cur.fetchall()
            results = results if results else [] 
            for item in results:
                if 'holder' not in item:
                    # only search special ap by mac, the holder field not existed
                    sql = 'select holder from holder_ap where mac = "{}"'.format(query)
                    cur.execute(sql)
                    record = cur.fetchone()
                    item['holder'] = record['holder'] if record else ''
            return results

    def bind_aps(self, holder, aps):
        '''
            bind ap to holder
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            for ap in aps:
                # mac address
                sql = 'insert into holder_ap (holder, mac) values({}, "{}")'.format(holder, ap)
                cur.execute(sql)
            conn.commit()

    def unbind_aps(self, holder, aps):
        '''
            unbind aps
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            for ap in aps:
                # mac address
                sql = 'delete from holder_ap where holder = {} and mac = "{}"'.format(holder, ap)
                cur.execute(sql)
            conn.commit()

    def remove_aps(self, aps):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            for ap in aps:
                sql = 'delete from aps where mac = "{}"'.format(ap)
                cur.execute(sql)
                sql = 'delete from holder_ap where mac = "{}"'.format(ap)
                cur.execute(sql)
            conn.commit()

    def add_holder_rooms(self, holder, rooms):
        '''
            holder: int
            rooms: ((room, password), )
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            mask = 2**1 + 2**8 + 2**9
            for room in rooms:
                # insert holder's account
                room_account = str(holder) + str(room)
                cur.execute('select * from bd_account where user = "{}"'.format(room_account))
                if not cur.fetchone():
                    # add new record
                    sql = '''insert into bd_account (user, password, mask, coin, holder, ends) 
                    values("{}", "{}", {}, 0, {}, 2)
                    '''.format(room_account, util.generate_password(), mask, holder)
                    cur.execute(sql)
            conn.commit()

    def remove_holder_room(self, holder, room):
        '''
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            user = '{}{}'.format(holder, room)
            sql = 'delete from userinfo where user = "{}"'.format(user)
            cur.execute(sql)
            # sql = 'delete from amount where user = {}'.format(user)
            # cur.execute(sql)
            sql = 'delete from bd_account where user = "{}" and holder = {}'.format(user, holder)
            cur.execute(sql)
            sql = 'delete from bind where renter = "{}"'.format(user)
            cur.execute(sql)
            conn.commit()

    def get_holder_renters(self, holder):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            # get holders
            # sql = '''select bd_account.*, account.realname, account.address from bd_account 
            # left join account on bd_account.user=cast(account.id as char) 
            # where bd_account.holder="{}"'''.format(holder)
            sql = '''select bd_account.*, account.realname, account.address from bd_account 
            left join account on bd_account.user=cast(account.id as char) 
            where bd_account.user="{}"'''.format(holder)
            cur.execute(sql)
            bd_account = cur.fetchone()
            sql = 'select user, password, mask, expired, ends from bd_account where holder = "{}" and user<>cast(holder as char)'.format(holder)
            cur.execute(sql)
            results = cur.fetchall()
            return bd_account, results

    def update_renter(self, user, **kwargs):
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            modify_str = ', '.join('{} = "{}"'.format(key, value) for key,value in kwargs.iteritems())
            sql = '''update bd_account set {} where user = "{}"
            '''.format(modify_str, id)
            cur.execute(sql)
            conn.commit()

    def update_renters(self, holder, rooms):
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            for room,fields in rooms.iteritems():
                room_account = str(holder) + str(room)
                sql = 'select * from bd_account where user = "{}"'.format(room_account)
                cur.execute(sql)
                if cur.fetchone():
                    modify_str = ', '.join('{} = "{}"'.format(key, value) for key,value in fields.iteritems())
                    sql = '''update bd_account set {} where user = "{}"
                    '''.format(modify_str, room_account)
                    cur.execute(sql)
                else:
                    sql = '''insert into bd_account (user, password, mask, expired, coin, holder, ends) 
                    values("{}", "{}", {}, "{}", 0, {}, {})
                    '''.format(room_account, fields['password'], fields['mask'], 
                               fields['expired'], holder, fields['ends'])
                    cur.execute(sql)
            conn.commit()

    def add_user(self, user, password, appid='', tid='', mobile='', ends=2**5):
        '''
            user : uuid or weixin openid
            password : user encrypted password
            ends : special the end type         data
                0 : unknown                     
                2^5 : weixin                      opendid

                2^6 : app(android)                opendid or other unique id 
                2^7 : app(ios)
                2^8 : mobile (verify mobile number)

                2**28 : acount forzened
                # 4 : web                         token & account
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            now = datetime.datetime.now()
            expired = now + datetime.timedelta(hours=6)
            now = now.strftime('%Y-%m-%d %H:%M:%S')
            expired = expired.strftime('%Y-%m-%d %H:%M:%S')
            sql, filters = '', ''
            column = 'uuid'
            if ends>>6 & 1:
                weixin, uuid = '', user
                mask = 0 + 2**2 + 2**6
                sql = 'insert into account (uuid, mask) values ("{}", {})'.format(user, mask)
                filters = 'account.uuid="{}" and account.mask={}'.format(user, mask)
            elif ends>>7 & 1:
                mask = 0 + 2**2 + 2**7
                sql = 'insert into account (uuid, mask) values ("{}", {})'.format(user, mask)
                filters = 'account.uuid="{}" and account.mask={}'.format(user, mask)
            elif ends>>8 & 1:
                column = 'mobile'
                mask = 0 + 2**2 + 2**8
                sql = 'insert into account (mobile, mask) values ("{}", {})'.format(mobile, mask)
                filters = 'account.mobile="{}" and account.mask={}'.format(user, mask)
            elif (ends>>5 & 1) and appid:
                # from weixin
                column = 'weixin'
                mask = 0 + 2**2 + 2**5
                sql = 'insert into account (appid, weixin, tid, mask)values ("{}", "{}", "{}", {})'.format(appid, user, tid, mask)
                filters = 'account.weixin="{}" and account.appid="{}" and account.mask={}'.format(user, appid, mask)

            cur.execute(sql)

            sql = 'select id from account where {} = "{}"'.format(column, user)
            if appid:
                sql = sql + ' and appid="{}"'.format(appid)

            cur.execute(sql)
            user = cur.fetchone()
            print(user)
            #
            # mask = mask + 2**9
            coin = 60
            user = str(user['id'])

            sql = '''insert into bd_account (user, password, mask, coin, expired, holder, ends, mobile) 
            values("{}", "{}", {}, {}, "{}", 0, 2, "{}")
            '''.format(user, password, mask, coin, expired, mobile)
            cur.execute(sql)
            conn.commit()

            sql = '''select bd_account.* from bd_account 
            left join account on bd_account.user=cast(account.id as char) 
            where {}'''.format(filters)
            cur.execute(sql)
            user = cur.fetchone()
            return user

    def update_user2(self, user, **kwargs):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            update_str = ', '.join(['{}="{}"'.format(key, value) for key,value in kwargs.iteritems()])
            sql = 'update bd_account set {} where user="{}"'.format(update_str, user)
            cur.execute(sql)

            if 'mobile' in kwargs:
                sql = 'update account set mobile="{}" where id={}'.format(kwargs['mobile'], user)
                cur.execute(sql)

            conn.commit()

    def remove_mac_history(self, user):
        '''
            delete user binded mac histories
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'delete from mac_history where user = "{}"'.format(user)
            cur.execute(sql)
            conn.commit()

    def remove_account(self, user):
        '''
            remove account
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            
            # remove binded records & nansha city binded records 
            sql = 'delete from pn_bind where user="{}"'.format(user)
            cur.execute(sql)

            # remove mac_history
            sql = 'delete from mac_history where user="{}"'.format(user)
            cur.execute(sql)

            # remove bd_account & account records
            sql = 'delete from bd_account where user="{}"'.format(user)
            cur.execute(sql)

            try:
                user = int(user, 10)
                sql = 'delete from account where id={}'.format(user)
                cur.execute(sql)
            except ValueError:
                # user can't convert to int, the account 
                pass

            conn.commit()

    def transfer_coin(self, user, to, coins):
        '''
            user 
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            # query from account's left coin
            sql = 'select coin from bd_account where user="{}"'.format(user)
            cur.execute(sql)
            _from = cur.fetchone()
            # query to account's left coin
            sql = 'select coin from bd_account where user="{}"'.format(to)
            _to = cur.execute(sql)
            
            # reduce from account's coin
            left = _from['coin'] - coins
            sql = 'update bd_account set coin={} where user=""'.format(left if left else 0, user)
            cur.execute(sql)
            # add coin to account  
            sql = 'update bd_account set coin={} where user=""'.format(_to['coin']+coins, to)
            cur.execute(sql)
            conn.commit()

    def get_user(self, user, ends=1<<5):
        '''
            arguments as add_user
        '''
        with Cursor(self.dbpool) as cur:
            # default from weixin
            column = 'weixin'
            if (ends & 1<<6) or (ends & 1<<7):
                column = 'uuid'
            cur.execute('select * from account where {} = "{}"'.format(column, user))
            user = cur.fetchone()
            return user

    def get_user2(self, user, ends=1<<5):
        with Connect(self.dbpool) as conn:
            conn.commit()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            column = 'weixin'
            if (ends & 1<<6) or (ends & 1<<7):
                column = 'uuid'
            cur.execute('select * from account where {} = "{}"'.format(column, user))
            user = cur.fetchone()
            return user


    def get_user_by_id(self, id):
        with Cursor(self.dbpool) as cur:
            cur.execute('select * from account where id = "{}"'.format(id))
            user = cur.fetchone()
            return user

    def get_bd_user(self, user):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            cur.execute('select * from bd_account where user = "{}"'.format(user))
            _user = cur.fetchone()
            if _user and _user['mask'] & 1<<5:
                # query weixin account binded renter
                sql = 'select * from bind where weixin = "{}"'.format(user)
                cur.execute(sql)
                record = cur.fetchone()
                if record:
                    sql = 'select expired from bd_account where user = "{}"'.format(record['renter'])
                    cur.execute(sql)
                    ret = cur.fetchone()
                    if ret and ret['expired'] > _user['expired']:
                        _user['expired'] = ret['expired']
            return _user

    def get_bd_user2(self, user):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            conn.commit()
            cur.execute('select * from bd_account where user = "{}"'.format(user))
            user = cur.fetchone()
            # if user and user['mask'] & 1<<5:
            #     # query weixin account binded renter
            #     sql = 'select * from bind where weixin = "{}"'.format(user)
            #     cur.execute(sql)
            #     record = cur.fetchone()
            #     if record:
            #         sql = 'select expired from bd_account where user = "{}"'.format(record['renter'])
            #         cur.execute(sql)
            #         ret = cur.fetchone()
            #         if ret:
            #             user['expired'] = ret['expired']
            return user

    def get_user_by_mac(self, mac):
        '''
            mac address : 
        '''
        with Cursor(self.dbpool) as cur:
            sql = 'select user, mac, tlogin from mac_history where mac="{}" order by tlogin'.format(mac)
            cur.execute(sql)
            _user = cur.fetchone()
            if _user:
                sql = 'select * from bd_account where user="{}"'.format(_user['user'])
                cur.execute(sql)
                _user = cur.fetchone()

            return _user


    # def get_bd_user_by_mac(self, user_mac):
    #     with Cursor(self.dbpool) as cur:
    #         sql = '''select bd_account.*, online.mac_addr from bd_account, 
    #         online where bd_account.user = online.user and 
    #         online.mac_addr = "{}"'''.format(user_mac)
    #         cur.execute(sql)
    #         user = cur.fetchone()
    #         return user

    def is_online(self, nas_addr, acct_session_id):
        '''
            
        '''
        with Cursor(self.dbpool) as cur:
            sql = 'select count(id) as online from online where \
                    nas_addr = "{}" and acct_session_id = "{}"'.format(nas_addr, acct_session_id)
            cur.execute(sql)
            return cur.fetchone()['online'] > 0

    def count_online(self, account):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            sql = 'select count(id) as online from online where user = "{}"'.format(account)
            cur.execute(sql)
            return cur.fetchone()['online']

    def get_online(self, nas_addr, acct_session_id):
        with Cursor(self.dbpool) as cur:
            sql = 'select * from online where \
                    nas_addr = "{}" and acct_session_id = "{}"'.format(nas_addr, acct_session_id)
            cur.execute(sql)
            return cur.fetchone()

    def get_user_onlines(self, user, mac):
        with Cursor(self.dbpool) as cur:
            sql = 'select nas_addr, acct_session_id, mac_addr, ap_mac, ssid, framed_ipaddr from online where user = "{}"'.format(user)
            if mac:
                sql = sql + ' and mac_addr = "{}"'.format(mac)
            cur.execute(sql)
            return cur.fetchall()

    def add_unauth_online(self, nas_addr, user, user_mac):
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = '''insert into online (user, nas_addr, acct_session_id, 
                acct_start_time, framed_ipaddr, mac_addr, billing_times, 
                input_total, output_total, start_source) values("{}", 
                "{}", "", "", "", "{}", 0, 0, 0, 0)
                '''.format(user, nas_addr, user_mac)
            cur.execute(sql)
            conn.commit()

    def add_online(self, online):
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            keys = ','.join(online.keys())
            vals = ','.join(['"%s"'%c for c in online.values()])
            sql = 'insert into online ({}) values({})'.format(keys, vals)
            # sql = '''update online set user="{}", nas_addr="{}", 
            # acct_session_id="{}", acct_start_time="{}", framed_ipaddr="{}", 
            # mac_addr="{}", start_source="{}" 
            # where user="{}" and mac_addr="{}"
            # '''.format(online['user'], online['nas_addr'], online['acct_session_id'], 
            #            online['acct_start_time'], online['framed_ipaddr'], 
            #            online['mac_addr'], online['start_source'], 
            #            online['user'], online['mac_addr'])
            cur.execute(sql)
            conn.commit()

    def update_online(self, online):
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            online_sql = '''update online set 
                billing_times = "{}",
                input_total = "{}",
                output_total = "{}",
                where nas_addr = "{}" and acct_session_id = "{}"
            '''.format(online['billing_times'], online['input_total'], 
                       online['output_total'], online['nas_addr'], 
                       online['acct_session_id'])
            cur.execute(online_sql)
            conn.commit()

    def update_billing(self, billing, time_length=0, flow_length=0, mask=0):
        '''  '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            # if mask>>2 & 1:
            #     # update account
            #     balance_sql = '''update bd_account set
            #         time_length = "{}", 
            #         flow_length = "{}" where user = "{}"
            #     '''.format(time_length, flow_length, billing['user'])
            #     cur.execute(balance_sql)

            # update online
            online_sql = '''update online set
                billing_times = "{}",
                input_total = "{}",
                output_total = "{}"
                where nas_addr = "{}" and acct_session_id = "{}"
            '''.format(billing['acct_session_time'], 
                       billing['input_total'], 
                       billing['output_total'],
                       billing['nas_addr'],
                       billing['acct_session_id'],
                      )
            cur.execute(online_sql)

            # update billing
            keys = ','.join(billing.keys())
            vals = ','.join(['"{}"'.format(c) for c in billing.values()])
            billing_sql = 'insert into billing ({}) values({})'.format(keys, vals)
            cur.execute(billing_sql)
            conn.commit()

    def del_online(self, nas_addr, acct_session_id):
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = '''delete from online where nas_addr = "{}" and 
                acct_session_id = "{}"'''.format(nas_addr, acct_session_id)
            cur.execute(sql)
            conn.commit()

    def add_ticket(self, ticket):
        _ticket = ticket.copy()
        for _key in _ticket:
            if _key not in ticket_fds:
                del ticket[_key]
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            keys = ','.join(ticket.keys())
            vals = ','.join(['"{}"'.format(c) for c in ticket.values()])
            sql = 'insert into ticket ({}) values({})'.format(keys, vals)
            cur.execute(sql)
            conn.commit()

    def unlock_online(self, nas_addr, acct_session_id, stop_source):
        bsql = '''insert into ticket (
            user, acct_session_id, acct_start_time, nas_addr, framed_ipaddr, start_source,
            acct_session_time, acct_stop_time, stop_source) values(
            "{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}")
        '''
        def _ticket(online):
            ticket = []
            ticket.append(online['user'])
            ticket.append(online['acct_session_id'])
            ticket.append(online['acct_start_time'])
            ticket.append(online['nas_addr'])
            ticket.append(online['framed_ipaddr'])
            ticket.append(online['start_source'])
            _datetime = datetime.datetime.now()
            _starttime = datetime.datetime.strptime(online['acct_start_time'], '%Y-%m-%d %H:%M:%S')
            session_time = (_datetime - _starttime).seconds
            stop_time = _datetime.strftime('%Y-%m-%d %H:%M:%S')
            ticket.append(session_time)
            ticket.append(stop_time)
            ticket.append(stop_source)
            return ticket

        def _unlock_one():
            ticket = None
            with Connect(self.dbpool) as conn:
                cur = conn.cursor(MySQLdb.cursors.DictCursor)
                sql = 'select * from online where nas_addr = "{}" and \
                        acct_session_id = "{}"'.format(nas_addr, acct_session_id)
                cur.execute(sql)
                online = cur.fetchone()
                if online:
                    ticket = _ticket(online)
                    dsql = 'delete from online where nas_addr = "{}" and \
                            acct_session_id = "{}"'.format(nas_addr, acct_session_id)
                    cur.execute(dsql)
                    cur.execute(bsql, ticket)
                    conn.commit()

        def _unlock_many():
            tickets = None
            with Connect(self.dbpool) as conn:
                cur = conn.cursor(MySQLdb.cursors.DictCursor)
                sql = 'select * from online where nas_addr = "{}" and \
                        acct_session_id = "{}"'.format(nas_addr, acct_session_id)
                cur.execute(sql)
                for online in cur:
                    tickets.append(_ticket(online))
                if tickets:
                    cur.executemany(bsql, tickets)
                    cur.execute('delete from online where nas_addr = "{}"'.format(nas_addr))
                    conn.commit()
        if acct_session_id:
            _unlock_one()
        else:
            _unlock_many()

    def bind(self, weixin, user):
        '''
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            # check weixin account 
            sql = 'select * from bd_account where user="{}" and mask>>5&1'.format(weixin)
            cur.execute(sql)
            record = cur.fetchone()
            if not record:
                return

            # check user type, must be renter room
            # cur.execute('select * from bd_account where user="{}" and mask>>8&1'.format(user))
            # record = cur.fetchone()
            # if not record:
            #     return
            sql = 'select * from bind where weixin = "{}"'.format(weixin)
            cur.execute(sql)
            if cur.fetchone():
                sql = 'update bind set renter = "{}" where weixin = "{}"'.format(user, weixin)
            else:
                sql = 'insert into bind (weixin, renter) values({}, {})'.format(weixin, user)
            cur.execute(sql)
            conn.commit()

    def unbind(self, weixin, user):
        '''
            unbind weixin account & renter account
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'delete from bind where weixin="{}"'.format(weixin)
            cur.execute(sql)
            conn.commit()

    #**************************************************
    #
    #
    #     private network method
    #
    #
    #**************************************************
    def query_avaiable_pns(self, user, mobile):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            sql = '''select pn_policy.* from pn_policy 
            right join information_schema.tables on concat('pn_', `pn`) = information_schema.tables.table_name 
            where pn_policy.policy&2
            '''
            cur.execute(sql)
            tables = cur.fetchall()

            results = []
            for item in tables:
                sql = 'select id from pn_{} where mobile="{}"'.format(item['pn'], mobile)
                cur.execute(sql)
                if cur.fetchone():
                    results.append(item)


            return results

    def bind_avaiable_pns(self, user, mobile):
        '''
        '''
        pass
        # with Connect(self.dbpool) as conn:
        #     cur = conn.cursor(MySQLdb.cursors.DictCursor)
        #     results = []

        #     cur.execute('select * from pn_policy where policy&2')
        #     pns = cur.fetchall()
        #     cur.execute('select table_name from information_schema.tables where table_name like "pn_%"')
        #     tables = cur.fetchall()

        #     tables = [item['table_name'] for item in tables]

        #     pns = [item for item in pns if 'pn_{}'.format(item['pn']) in tables]


        #     for item in pns:
        #         sql = 'select id from pn_{} where mobile = "{}"'.format(item['pn'], mobile)
        #         cur.execute(sql)
        #         if cur.fetchone():
        #             results.append(item)

        #     if results:
        #         for item in results:
        #             sql = 'insert into pn_bind(user, holder, mobile) values("{}", {}, "{}")'.format(user, item['pn'], mobile)
        #             try:
        #                 cur.execute(sql)
        #             except MySQLdb.IntegrityError:
        #                 # existed bind pair
        #                 pass

        #     conn.commit()
        #     return results

    def  get_wx_config(self):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            cur.execute('select * from wx')
            return cur.fetchall()


    def get_pns(self):
        with Cursor(self.dbpool) as cur:
            sql = 'select * from pn_policy'
            cur.execute(sql)
            return cur.fetchall()


    def create_pn(self, **kwargs):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            keys = ', '.join(kwargs.keys()) 
            values = ', '.join(['"{}"'.format(item) for item in kwargs.values()])
            sql = 'insert into pn_policy ({}) values({})'.format(keys, values)

            cur.execute(sql)
            conn.commit()

    def update_pn(self, pn, **kwargs):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            modify_str = ', '.join(['{}="{}"'.format(key, value) for key,value in kwargs.iteritems()])
            sql = 'update pn_policy set {} where pn={}'.format(modify_str, pn)
            cur.execute(sql)
            conn.commit()

    def add_pn_account(self, table, **kwargs):
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            keys = ', '.join(kwargs.keys()) 
            values = ', '.join(['"{}"'.format(item) for item in kwargs.values()])
            sql = 'insert into {} ({}) values({})'.format(table, keys, values)
            cur.execute(sql)
            sql = 'select id from {} where mobile = {}'.format(table, kwargs['mobile'])
            cur.execute(sql)
            _id = cur.fetchone()['id']
            conn.commit()
            return _id

    def update_pn_account(self, table, _id, **kwargs):
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            modify_str = ', '.join(['{}="{}"'.format(key, value) for key,value in kwargs.iteritems()])
            sql = 'update {} set {} where id={}'.format(table, modify_str, _id)
            cur.execute(sql)
            conn.commit()

    def get_pn_account(self, table, **kwargs):
        with Cursor(self.dbpool) as cur:
            query_str = self._combine_query_kwargs(**kwargs)
            sql = 'select * from {} where {}'.format(table, query_str)
            cur.execute(sql)
            return cur.fetchone()

    def bind_pn_account(self, holder, user, mobile):
        '''
            bind user & mobile account in pn_bind
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            # found previous binded pairs
            # sql = 'select * from bind where weixin="pn_{}" and renter="{}"'.format(user, holder)
            sql = 'insert into pn_bind (user, holder, mobile) values("{}", {}, "{}")'.format(user, holder, mobile)
            cur.execute(sql)
            conn.commit()


    def unbind_pn_account(self, holder, mobile):
        '''
            unbind holder's user & mobile bind pairs in pn_bind
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'delete from pn_bind where holder={} and mobile="{}"'.format(holder, mobile)
            cur.execute(sql)
            conn.commit()

    def delete_pn_account(self, holder, mobile):
        '''
            private network manager delete his record:
                1. delete holder's binded pairs
                2. delete holder's account record
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            # delete binded pairs
            sql = 'delete from pn_bind where holder={} and mobile="{}"'.format(holder, mobile)
            cur.execute(sql)

            # delete holder's account record
            sql = 'delete from pn_{} where mobile="{}"'.format(holder, mobile)
            cur.execute(sql)
            conn.commit()

    # def get_employee_binded_account(self, mobile):
    #     '''
    #         nan sha binded account 
    #         employee's mobile number & bd_account
    #     '''
    #     with Cursor(self.dbpool) as cur:
    #         sql = 'select * from bind where mobile = "ns_{}"'.format(mobile)
    #         cur.execute(sql)
    #         results = cur.fetchall()
    #         return results if results else []

    # def bind_ns_employee(self, mobile, user):
    #     '''
    #         bind nan sha employee account with bd_account
    #         do two steps:
    #             1. add bind record (ns_mobile, user)
    #             2. modify account's mask(| 1<<16)
    #     '''
    #     with Connect(self.dbpool) as conn:
    #         cur = conn.cursor(MySQLdb.cursors.DictCursor)
    #         sql = 'select * from bind where weixin="ns_{}" and renter="{}"'.format(mobile, user['user'])
    #         cur.execute(sql)
    #         if not cur.fetchone():
    #             # not existed, add new record
    #             sql = 'insert into bind (weixin, renter) values("ns_{}", "{}")'.format(mobile, user['user'])
    #             cur.execute(sql)
    #         # set user's mask(1<<16), nansha employee flags
    #         if not (user['mask'] & 1<<16):
    #             # set 1<<16
    #             mask = user['mask'] | (1<<16) 
    #             sql = 'update bd_account set mask = {} where user = "{}"'.format(mask, user['user']) 
    #             cur.execute(sql)
    #         conn.commit()



    # def unbind_ns_employee(self, mobile, user):
    #     '''
    #     '''
    #     with Connect(self.dbpool) as conn:
    #         cur = conn.cursor(MySQLdb.cursors.DictCursor)
    #         sql = 'delete from bind where weixin="ns_{}" and renter="{}"'.format(mobile, user)
    #         cur.execute(sql)
    #         conn.commit()


    #**********************************************************
    #
    #
    # Nan sha notice 
    #
    #
    #**********************************************************
    def publish_notice(self, **kwargs):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            keys = ', '.join(kwargs.keys())
            values = ', '.join(['"{}"'.format(item) for item in kwargs.values()])
            sql = 'insert into ns_notice ({}) values({})'.format(keys, values)
            cur.execute(sql)
            conn.commit()

    def update_notice(self, _id, **kwargs):
        '''
            update existed fields
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            modify_str = ', '.join(['{}="{}"'.format(key,value) for key,value in kwargs.iteritems()])
            sql = 'update ns_notice set {} where id = {}'.format(modify_str, _id)
            cur.execute(sql)
            conn.commit()

    def remove_notice(self, _id):
        '''
            _id : 
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'delete from ns_notice where id = {}'.format(_id)
            cur.execute(sql)
            conn.commit()

    def get_notices(self, start, mask, per):
        '''
            get per records from start
        '''
        with Cursor(self.dbpool) as cur:
            sql = 'select * from ns_notice where mask = {} order by id desc limit {}, {}'.format(mask, start, per)
            cur.execute(sql)
            results = cur.fetchall()
            return results if results else []

    def get_notice(self, _id):
        '''
            get special notice
        '''
        with Cursor(self.dbpool) as cur:
            sql = 'select * from ns_notice where id = {}'.format(_id)
            cur.execute(sql)
            return cur.fetchone()


# database_config = settings['database_config']

db = Store()
db.setup(settings)
# import sys
# sys.modules[__name__] = db


