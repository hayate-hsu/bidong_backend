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
            maxusage=config['maxusage']
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

    # *********************************************
    #
    # group operator
    #
    # *********************************************
    def create_group(self, name, note):
        '''
            name : unique index
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'insert into groups (name, note) values("{}", "{}")'.format(name, note)
            cur.execute(sql)
            conn.commit()

    def get_group(self, _id):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            sql = 'select * from groups where id = {}'.format(_id)
            cur.execute(sql)
            return cur.fetchone()

    def get_groups(self):
        '''
            get groups and sorted ascending
        '''
        with Cursor(self.dbpool) as cur:
            sql = 'select * from groups order by id'
            cur.execute(sql)
            results = cur.fetchall()
            return results if results else []

    def create_gmtype(self, group, name):
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'insert into gmtype (group, name) values({}, "{}")'.format(group, name)
            cur.execute(sql)
            conn.commit()

    def get_gmtype(self, group, _id):
        with Cursor(self.dbpool) as cur:
            sql = 'select * from gmtype where id = {} and groups = {}'.format(_id, group)
            cur.execute(sql)
            return cur.fetchone()

    def get_gmtypes(self, group):
        with Cursor(self.dbpool) as cur:
            sql = 'select * from gmtype where groups = {} order by id'.format(group)
            cur.execute(sql)
            results = cur.fetchall()
            return results if results else []

    def delete_gmtype(self, group, _id):
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'delete from gmtype where id = {} and groups = {}'.format(_id, group)
            cur.execute(sql)
            conn.commit()


    # *********************************************
    #
    # group operator
    #
    # *********************************************
    def create_manager(self, **kwargs):
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            key_str = ', '.join(kwargs.keys())
            value_str = ', '.join(['"{}"'.format(item) for item in kwargs.values()])
            sql = 'insert into manager ({}) values({})'.format(key_str, value_str)
            cur.execute(sql)
            conn.commit()

    def update_manager(self, user, **kwargs):
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            modify_str = ', '.join('{} = "{}"'.format(key,value) for key,value in kwargs.iteritems())
            sql = 'update manager set {} where user = "{}"'.format(modify_str, user)
            cur.execute(sql)
            conn.commit()

    def delete_manager(self, user):
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'delete from manager where user = "{}"'.format(user)
            cur.execute(sql)
            conn.commit()

    def get_manager(self, user):
        with Cursor(self.dbpool) as cur:
            sql = 'select * from manager where user = "{}"'.format(user)
            cur.execute(sql)
            return cur.fetchone()

    def get_managers(self):
        with Cursor(self.dbpool) as cur:
            sql = 'select * from manager'
            cur.execute(sql)
            results = cur.fetchall()

            return results if results else []

    # *********************************************
    #
    # message operator
    #
    # *********************************************
    def add_section(self, name):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'insert into section (name) values("{}")'.format(name)
            cur.execute(sql)
            conn.commit()

    def delete_section(self, _id):
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'delete from section where id={}'.format(_id)
            cur.execute(sql)
            conn.commit()

    def get_section(self, _id):
        with Cursor(self.dbpool) as cur:
            sql = 'select * from section where id={}'.format(_id)
            cur.execute(sql)
            return cur.fetchone()

    def get_sections(self):
        with Cursor(self.dbpool) as cur:
            sql = 'select * from section'
            cur.execute(sql)
            results = cur.fetchall()
            return results if results else []

    def create_message(self, **kwargs):
        '''
            create new message
            each message distinguished by id [md5(author, title, subtitle, content)]
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            key_str = ', '.join(kwargs.keys())
            value_str = ', '.join(["'{}'".format(item) for item in kwargs.values()])
            sql = 'insert into message ({}) values({})'.format(key_str, value_str)
            cur.execute(sql)
            conn.commit()

    def update_message(self, _id, **kwargs):
        '''
            update message's property
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            modify_str = ', '.join("{} = '{}'".format(key,value) for key,value in kwargs.iteritems())
            sql = 'update message set {} where id = "{}"'.format(modify_str, _id)
            cur.execute(sql)
            conn.commit()

    def delete_message(self, _id):
        '''
            delete special message
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'delete from message where id = "{}"'.format(_id)
            cur.execute(sql)
            conn.commit()

    def get_message(self, _id):
        '''
            get special message
        '''
        with Cursor(self.dbpool) as cur:
            sql = '''select message.*, section.name as section from message, section 
            where message.id="{}" and message.section = section.id'''.format(_id)
            cur.execute(sql)
            return cur.fetchone()

    def get_messages(self, groups, mask, isimg, gmtype, label, pos, nums=10):
        '''
            id title subtitle section mask author groups status ctime content image
            get groups's messages excelpt content filed
            order by ctime desc 
            groups : message's group
            mask : message type (combine by bit operator)
            pos : where to get special messages
            isimg : search messages which image <> '';
        '''
        with Cursor(self.dbpool) as cur:
            filters = 'message.id, message.title, message.subtitle, message.mask, message.author, message.groups, message.status, message.ctime, message.image'
            sql = ''
            gmtype = 'message.gmtype = {} and '.format(gmtype) if gmtype else ''
            isimg = 'message.image <> "" and '.format(isimg) if isimg else ''
            label = " and label like'%{}%'".format(label) if label else ''

            if mask:
                sql = '''select {}, section.name as section from message, section 
                where {}{}message.groups = {} and message.mask & {} = {} and 
                message.section = section.id order by message.status desc, message.ctime desc limit {},{}
                '''.format(filters, gmtype, isimg, groups, __MASK__, mask, pos, nums)
            else:
                # doesn't check message type
                sql = '''select {}, section.name as section from message, section 
                where {}{}message.groups = {} and message.section = section.id{} 
                order by message.status desc, message.ctime desc limit {},{}
                '''.format(filters, gmtype, isimg, groups, label, pos, nums)

            cur.execute(sql)
            results = cur.fetchall()
            return results if results else []

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

    # def get_manager(self, user, mask):
    #     '''
    #         maks (binary mask)
    #             0 : admin    # bit 0 set or unset 
    #             1 : bidong
    #             2 : nansha
    #     '''
    #     with Cursor(self.dbpool) as cur:
    #         sql = ''
    #         if mask == 0:
    #             sql = 'select * from manager where user = "{}"'.format(user)
    #         else:
    #             sql = 'select * from manager where user = "{}" and mask & 1<<{}'.format(user, mask)
    #         cur.execute(sql)
    #         return cur.fetchone()

    def get_account(self, **kwargs):
        '''
            get account's info
        '''
        with Cursor(self.dbpool) as cur:
            query_str = self._combine_query_kwargs(**kwargs)
            sql = 'select * from account where {}'.format(query_str)
            cur.execute(sql)
            return cur.fetchone()

    def add_holder(self, weixin, password, mobile, expire_date,
                      email='', address='', realname='', portal='login.html', billing=0):
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
                sql = '''update account set mask = {}, mobile = "{}", expire_date="", 
                email="{}", address="{}", realname="{}" where id = {}
                '''.format(mask, mobile, email, address, realname, user['id'])
                cur.execute(sql)

                # sql = 'select mask from bd_account where user = "{}"'.format(user['id'])
                # cur.execute(sql)
                # _user = cur.fetchone()
                # mask = _user['mask'] + 2**8 + 2**3
                # sql = 'update bd_account set mask = {} where user = "{}"'.format(mask, _user['user'])
                # cur.execute(sql)
            else:
                mask = 0 + 2**1
                # if weixin:
                #     mask = mask + 2**5
                # insert holder account
                sql = '''insert into account 
                (mobile, weixin, uuid, email, mask, address, 
                realname, create_time, expire_date) 
                values("{}", "{}", "", "{}", {}, "{}", "{}", "{}", "{}")
                '''.format(mobile, weixin, email, mask, address, 
                           realname, now, expire_date)
                cur.execute(sql)
                sql = 'select id from account where mobile = "{}"'.format(mobile)
                cur.execute(sql)
                user = cur.fetchone()

                mask = mask + 2**8 + 2**3

                sql = '''insert into bd_account (user, password, mask, expire_date, coin, holder, ends) 
                values("{}", "{}", {}, "{}", 0, {}, 2)
                '''.format(str(user['id']), password, mask, expire_date, user['id'])
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
            sql = '''select id, realname, mobile, mask, address, expire_date, portal, policy from account 
            where mask & 3 = {} order by id desc limit {}, {}'''.format(mask, start, per)
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
                modify_dict['mask'] = _user['mask'] | 1 | (1<<3) | (1<<8)
                modify_dict['holder'] = holder
            elif frozen == 1 and mask and mask & 1<<30:
                modify_dict['mask'] = _user['mask'] | 1<<30
            elif frozen == 0 and mask and not (mask & 1<<30):
                # account unforzen
                modify_dict['mask'] = (_user['mask'] ^ 1<<30) if (_user['mask'] & 1<<30) else _user['mask']

            if 'expire_date' in kwargs:
                modify_dict['expire_date'] = kwargs['expire_date']

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

            # update holder's billing settings
            modify_dict = {}
            if 'portal' in kwargs:
                modify_dict['portal'] = kwargs['portal']
            if 'policy' in kwargs:
                modify_dict['policy'] = kwargs['policy']
            if modify_dict:
                modify_str = ', '.join('{} = "{}"'.format(key,value) for key,value in modify_dict.iteritems())
                sql = 'update account set {} where id = {}'.format(modify_str, holder)
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
            mask = 2**1 + 2**8
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

    # def get_holder_rooms(self, holder):
    #     '''
    #     '''
    #     with Cursor(self.dbpool) as cur:
    #         sql = 'select room from holder_room where holder = "{}"'.format(holder)
    #         cur.execute(sql)
    #         results = cur.fetchall()

    #         return results if results else ()

    def remove_holder_room(self, holder, room):
        '''
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            user = '{}{}'.format(holder, room)
            sql = 'delete from bd_account where user = {} and holder = {}'.format(user, holder)
            cur.execute(sql)
            sql = 'delete from bind where renter = "{}"'.format(user)
            cur.execute(sql)
            conn.commit()

    def get_holder_renters(self, holder):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            sql = 'select user, password, mask, expire_date, ends from bd_account where holder = "{}"'.format(holder)
            cur.execute(sql)
            results = cur.fetchall()
            return results

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
                    sql = '''insert into bd_account (user, password, mask, expire_date, coin, holder, ends) 
                    values("{}", "{}", {}, "{}", 0, {}, {})
                    '''.format(room_account, fields['password'], fields['mask'], 
                               fields['expire_date'], holder, fields['ends'])
                    cur.execute(sql)
            conn.commit()

    def add_user(self, user, password, ends=2**5):
        '''
            user : uuid or weixin openid
            password : user encrypted password
            ends : special the end type         data
                0 : unknown                     
                2^5 : weixin        opendid
                2^6 : app (android) opendid or other unique id 
                2^7 : app (ios)
                2**9: user pay by time

                2**28 : acount forzened
                # 4 : web                         token & account
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            column = 'weixin'
            weixin, uuid = user, ''
            mask = 0 + 2**2 + 2**5
            if ends>>6 & 1:
                weixin, uuid = '', user
                column = 'uuid'
                mask = 0 + 2**2 + 2**6
            elif ends>>7 & 1:
                weixin, uuid = '', user
                column = 'uuid'
                mask = 0 + 2**2 + 2**7

            sql = '''insert into account 
            (mobile, weixin, uuid, email, mask, address, realname, create_time) 
            values("", "{}", "{}", "", {}, "", "", "{}")
            '''.format(weixin, uuid, mask, now)
            cur.execute(sql)

            sql = 'select id from account where {} = "{}"'.format(column, user)
            cur.execute(sql)
            user = cur.fetchone()
            print(user)
            #
            # mask = mask + 2**9
            coin = 60

            sql = '''insert into bd_account (user, password, mask, coin, holder, ends) 
            values("{}", "{}", {}, {}, 0, 5)
            '''.format(str(user['id']), password, mask, coin)
            cur.execute(sql)
            conn.commit()
            return user['id']# , password, mask, time_length

    def update_user(self, user, account):
        '''
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'update account set mask = {} where weixin = "{}"'.format(account['mask'], user) 
            cur.execute(sql)
            # sql = 'update bd_account set mask = {} where user = "{}"'.format(account['mask'], str(account['id'])) 
            # cur.execute(sql)
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
            sql = 'delete from bind where weixin="{}" or renter="{}"'.format(user, user)
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

    def update_user2(self, user, **kwargs):
        '''
            update bd_account info 
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            update_str = ', '.join(['{}="{}"'.format(key, value) for key,value in kwargs.iteritems()])
            sql = 'update bd_account set {} where user = "{}"'.format(update_str, user)
            cur.execute(sql)
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
            if ends & 1<<6:
                # from app
                column = 'uuid'
            cur.execute('select * from account where {} = "{}"'.format(column, user))
            user = cur.fetchone()
            return user

    def get_user_by_id(self, id):
        with Cursor(self.dbpool) as cur:
            cur.execute('select * from account where id = "{}"'.format(id))
            user = cur.fetchone()
            return user

    def add_bd_user(self, user, password):
        '''
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = '''insert into bd_account (user, password, mask, coin, ends)
            values(%s, %s, 3, 60, 2)'''
            cur.execute(sql, user, password)
            conn.commit()

    def update_bd_user(self, user, **kwargs):
        '''
            update bd info
        '''
        with Connect(self.dbpool) as conn:
            # cur = conn.cursor()
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            modify_str = ', '.join('{} = "{}"'.format(key, value) for key,value in kwargs.iteritems())
            sql = '''update bd_account set {} where user = "{}"
            '''.format(modify_str, user)
            cur.execute(sql)
            conn.commit()

    def get_bd_user(self, user):
        '''
        '''
        with Cursor(self.dbpool) as cur:
            cur.execute('select * from bd_account where user = "{}"'.format(user))
            user = cur.fetchone()
            if user and user['mask'] & 1<<5:
                # query weixin account binded renter
                sql = 'select * from bind where weixin = "{}"'.format(user)
                cur.execute(sql)
                record = cur.fetchone()
                if record:
                    sql = 'select expire_date from bd_account where user = "{}"'.format(record['renter'])
                    cur.execute(sql)
                    ret = cur.fetchone()
                    if ret:
                        user['expire_date'] = ret['expire_date']
            return user

    def get_bd_user_by_mac(self, user_mac):
        with Cursor(self.dbpool) as cur:
            sql = '''select bd_account.*, online.mac_addr from bd_account, 
            online where bd_account.user = online.user and 
            online.mac_addr = "{}"'''.format(user_mac)
            cur.execute(sql)
            user = cur.fetchone()
            return user

    def get_block_user(self, mac):
        '''
            mac : mac address
        '''
        pass

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

    def merge_app_account(self, _id, user):
        '''
            merge mac account to app account
            _id : new created app account
            user : mac address remove ':'
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'select * from bd_account where user="{}"'.format(user)
            cur.execute(sql)
            _user = cur.fetchone()
            if _user:
                # delete mac history record
                sql = 'delete from mac_history where user="{}"'.format(user)
                cur.execute(sql)
                # delete bd_account
                sql = 'delete from bd_account where user="{}"'.format(user)
                cur.execute(sql)

                # update app account's expire_date & coin
                sql = '''update bd_account set expire_date="{}", coin={} 
                where user="{}"'''.format(_user['expire_date'], _user['coin'], _id)
                cur.execute(sql)

                # update binded account
                sql = 'update bind set weixin="{}" where weixin="{}"'.format(_id, user)
                cur.execute(sql)

                if _user['mask'] & 1<<16:
                    # update nansha employee mapped
                    sql = 'update bind set renter="{}" where renter="{}"'.format(_id, user)
                    cur.execute(sql)

                conn.commit()
    
    #**************************************************
    #
    #
    #     nan sha employee manager
    #
    #
    #**************************************************
    def add_ns_employee(self, **kwargs):
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            keys = ', '.join(kwargs.keys()) 
            values = ', '.join(['"{}"'.format(item) for item in kwargs.values()])
            sql = 'insert into ns_employee ({}) values({})'.format(keys, values)
            cur.execute(sql)
            sql = 'select id from ns_employee where mobile = {}'.format(kwargs['mobile'])
            cur.execute(sql)
            _id = cur.fetchone()['id']
            conn.commit()
            return _id

    def update_ns_employee(self, _id, **kwargs):
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            modify_str = ', '.join(['{}="{}"'.format(key, value) for key,value in kwargs.iteritems()])
            sql = 'update ns_employee set {} where id={}'.format(modify_str, _id)
            cur.execute(sql)
            conn.commit()

    def get_ns_employee(self, **kwargs):
        with Cursor(self.dbpool) as cur:
            # query_list = []
            # for key,value in kwargs.iteritems():
            #     if isinstance(value, int):
            #         query_list.append('{}={}'.format(key, value))
            #     else:
            #         query_list.append('{}="{}"'.format(key, value))
            # query_str = 'and '.join(query_list)
            query_str = self._combine_query_kwargs(**kwargs)
            sql = 'select * from ns_employee where {}'.format(query_str)
            cur.execute(sql)
            return cur.fetchone()

    def get_employee_binded_account(self, mobile):
        '''
            nan sha binded account 
            employee's mobile number & bd_account
        '''
        with Cursor(self.dbpool) as cur:
            sql = 'select * from bind where mobile = "ns_{}"'.format(mobile)
            cur.execute(sql)
            results = cur.fetchall()
            return results if results else []

    def bind_ns_employee(self, mobile, user):
        '''
            bind nan sha employee account with bd_account
            do two steps:
                1. add bind record (ns_mobile, user)
                2. modify account's mask(| 1<<16)
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'select * from bind where weixin="ns_{}" and renter="{}"'.format(mobile, user['user'])
            cur.execute(sql)
            if not cur.fetchone():
                # not existed, add new record
                sql = 'insert into bind (weixin, renter) values("ns_{}", "{}")'.format(mobile, user['user'])
                cur.execute(sql)
            # set user's mask(1<<16), nansha employee flags
            if not (user['mask'] & 1<<16):
                # set 1<<16
                mask = user['mask'] | (1<<16) 
                sql = 'update bd_account set mask = {} where user = "{}"'.format(mask, user['user']) 
                cur.execute(sql)
            conn.commit()

    def unbind_ns_employee(self, mobile, user):
        '''
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'delete from bind where weixin="ns_{}" and renter="{}"'.format(mobile, user)
            cur.execute(sql)
            conn.commit()

    def delete_ns_employee(self, mobile):
        '''
            delete nan sha employee account binded bd_account
            do three steps:
                1. query binded bd_account
                2. set account's mask (^ 1<<16)
                3. delete binded record
        '''
        with Connect(self.dbpool) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            sql = 'select * from bind where weixin = "ns_{}"'.format(mobile)
            cur.execute(sql)
            records = cur.fetchall()
            for record in records:
                sql = 'select user, mask from bd_account where user = "{}"'.format(record['renter'])
                cur.execute(sql)
                record = cur.fetchone()
                if record:
                    mask = record['mask']
                    if mask & (1<<16):
                        mask = mask ^ 1<<16
                        sql = 'update bd_account set mask = {} where user = "{}"'.format(mask, record['user'])
                        cur.execute(sql)
            # delete binded records
            sql = 'delete from bind where weixin = "ns_{}"'.format(mobile)
            cur.execute(sql)

            # delete ns_employee record
            sql = 'delete from ns_employee where mobile = "{}"'.format(mobile)
            cur.execute(sql)

            conn.commit()

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


