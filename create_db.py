#!/usr/bin/env python
#coding:utf-8
'''
    create database's tables
'''

# create groups
# name : groups name (company & production)
group_sql = '''
create table if not exists groups (id int(11) unsigned not null auto_increment,
name varchar(32) not null,  
note varchar(64) not null default '',
primary key (id), 
unique index idx_groups_name (name))
auto_increment = 1000;
'''

# create manager
manager_sql = '''
create table if not exists manager (user varchar(24) not null default '',
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
