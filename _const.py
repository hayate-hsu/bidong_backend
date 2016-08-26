#!/usr/bin/env python
#coding:utf-8
message = {
404:u'账号不存在',
453:u'非房东账号',

'account':'上网账号: {}\n账号密码： {}\n\n',

'welcome':'欢迎关注壁咚无线\n你的上网账号: {}\n密码: {}\n\n<a href="http://wnl.bidongwifi.com:9899/help.html">上网帮助，请点这里</a>\n\n',

'msg_template':'动态验证码{}，用于身份验证或上网认证，有效期10分钟，请勿泄漏。',
}



import sys
sys.modules[__name__] = message
