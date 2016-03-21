#!/usr/bin/env python
#coding:utf-8
'''
    create database's tables
'''
# create bas table
# pip & port : ac http server address
# user & password : used for http login 
bas_sql = '''
create table if not exists bas (
id int(11) unsigned not null auto_increment,
vendor varchar(32) not null default '',
ip varchar(15) not null default '',
name varchar(64) not null default '',
model varchar(32) not null default '',
secret varchar(32) not null default '',
coa_port int(11) unsigned not null default 2000,
tz smallint(6),
pip varchar(15) not null default '',
port smallint(6) unsigned not null default 0,
user varchar(32) not null default '',
password varchar(32) not null default '',
primary key (id))
auto_increment = 1;
'''

# create account table
# ispri : 
#    0 : open, everyone can access this network 
#    1 : private, only id's permit users can access this network
account_sql = '''
create table if not exists account (
id int(11) unsigned not null auto_increment,
mobile varchar(17) not null default '',
weixin varchar(32) not null default '',
uuid varchar(40) not null default '',
email varchar(64) not null default '',
mask int(11) not null default 0,
address varchar(128) not null default '',
realname varchar(32) not null default '',
create_time varchar(19) not null default '',
expire_date varchar(10) not null default '',
portal varchar(64) not null default '',
policy smallint(6) not null default 0,
note varchar(128) not null default '',
ispri tinyint(1) not null default 0, 
primary key (id),
unique index account_app_weixin(appid, weixin))
auto_increment = 10000;
'''

# create wx table
wx = '''
create  table if not exists wx (
id int(11) unsigned not null auto_increment,
appid varchar(32) not null,
secret varchar(64) not null,
token varchar(64) not null,
key varchar(64) not null default '',
note varchar(128) not null default '',
ctime datetime not null default current_timestamp,
primary key (id),
unique index wx_appid (appid))
auto_increment = 1000;
)
'''

# create wx_subscribe table
wx_subscribe = '''
create table if not exists wx_subscribe (
id int(11) unsigned not null auto_increment,
appid varchar(24) not null,
user int(11) unsigned not null,
subscribe tinyint(1) not null,
openid varchar(32) not null,

nickname varchar(32) not null,
sex tinyint not null default 0,
language varchar(12) not null,
headimgurl varchar(256) not null default '',
subscribe_time datetime not null default current_timestamp,
unionid varchar(32) not null default '',
remark varchar(64) not null default '',
groupid int(11) not null default 0,
primary key (id))
auto_increment = 10000;
'''

# ssid settings
# note : network's name, 
pn_policy_sql = '''
create table if not exists policy (
pn int(11) unsigned not null ,
portal varchar(64) not null default 'login.html',
policy smallint(6) not null default 0,
note varchar(128) not null default '',
ispri tinyint(1) not null default 0,
ssid varchar(24) not null default '',
logo varchar(128) not null default '',
primary key (pn)) 
auto_increment = 10000;
'''

# create groups
# name : groups name (company & production)
group_sql = '''
create table if not exists groups (
id int(11) unsigned not null auto_increment,
name varchar(32) not null,  
note varchar(64) not null default '',
primary key (id), 
unique index idx_groups_name (name),
primary key (id))
auto_increment = 1000;
'''

# create manager
manager_sql = '''
create table if not exists manager (
user varchar(24) not null default '',
password varchar(32) not null default '',
mask int(11) unsigned not null default 0,
groups int(11) unsigned not null,
ctime datetime not null default current_timestamp,
primary key (user));
'''

# create section table, news type
section_sql = '''
create table if not exists section (
id int(11) unsigned not null auto_increment,
name varchar(32) not null default '',
primary key (id),
unique index idx_section_name (name));
'''
# sections
sections = {'Unknown', u'社会', u'娱乐', u'科技', u'经济', u'健康', }

# mgtype
gmtype_sql = '''
create table if not exists gmtype (
id int(11) unsigned not null auto_increment,
groups int(11) unsigned not null default 0,
name varchar(32) not null default '',
primary key (id),
unique index idx_gmtype_name (name));
'''

# create message table
# gmtype: group message type
message_sql = '''
create table if not exists message (
id char(32) not null,
title varchar(128) not null default '',
subtitle varchar(128) not null default '',
section int(11) unsigned not null default 0,
mask int(11) unsigned not null default 0,
author varchar(24) not null default '',
groups int(11) unsigned not null default 0,
status int(11) unsigned not null default 0,
gmtype int(11) unsigned not null default 0,
label varchar(64) not null default '',
ctime datetime not null default current_timestamp,
content text not null default '',
image varchar(64) not null default '',
primary key (id));
'''

# create app_ver
app_ver_sql = '''
create table if not exists app_ver_sql (pt varchar(24) not null default '',
newest varchar(12) not null default '',
least varchar(12) not null default '',
note varchar(256) not null default '',
primary key (pt))
'''

# nansha employee table
ns_employee = '''
create table if not exists ns_employee (
id int(11) unsigned not null auto_increment,
name varchar(32) not null default '',
gender tinyint(1) not null default 0,
mobile varchar(17) not null default '',
phone varchar(17) not null default '',
position varchar(32) not null default '',
department varchar(32) not null default '',
ctime datetime not null default current_timestamp,
mtime datetime not null default current_timestamp,
primary key (id), 
unique index idx_ns_employee_mobile (mobile))
auto_increment = 1000;
'''

# bd_account table
bd_account = '''
create table if not exists bd_account (
user varchar(32) not null default '',
password varchar(32) not null default '',
mask int(11) unsigned not null default 0,
time_length int(11) unsigned not null default 0,
flow_length int(11) unsigned not null default 0,
coin int unsigned not null default 0,
expire_date datetime,
ends int(11) unsigned not null default 2,
holder int(11) unsigned not null default 0,
mobile varchar(17) not null default '',
primary key (user));
'''

# private_network
# pn_holder
pn_holder = '''
create table if not exists pn_holder (
id int(11) unsigned not null auto_increment,
name varchar(32) not null default '',
gender tinyint(1) not null default 0,
mobile varchar(17) not null default '',
phone varchar(17) not null default '',
position varchar(32) not null default '',
department varchar(32) not null default '',
ctime datetime not null default current_timestamp,
mtime datetime not null default current_timestamp,
primary key (id), 
unique index idx_ns_employee_mobile (mobile))
auto_increment = 1000;
'''


# bind table : record bind paris
bind_sql = '''
create table if not exists pn_bind (
id int(11) unsigned not null auto_increment,
user varchar(24) not null default '',
holder int(11) unsinged not null default 0,
mobile varchar(17) not null default '',
primary key (id),
unique index idx_bind_pairs(holder, mobile))
auto_increment = 10000;
'''
