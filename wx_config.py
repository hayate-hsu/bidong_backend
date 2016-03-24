#!/usr/bin/env python2.7
#coding:utf-8
'''
weixin services configurations
'''

configure = {
    'bidong2' : {
        'grant_type':'client_credential',
        'appid':'wxa7c14e6853105a84',
        'secret':'668cd43eeff4e3238f6a95c0bc5c9840',
        'token':'bidongwifi173',
        'key':'28JAs3DjH2hi9t2R7YqCs27EN3T81gfJiXXkSwafEAz',
        'expire':7200,
        'note':'壁咚微信服务号-工研院',
    }, 

    'sufuwu' : {
        'grant_type':'client_credential',
        'appid':'wx5a9d6bdf40169d4f',				 
        'secret':'769cdc33bd43104205791b20bf2de5a7',
        'token':'sufuwu0321',
        'key':'c7Mu3tMNeQYfiu2ABk5Uq5HkyCxRG9znKQzrhZwXNOP',
        'expire':7200,
        'note':'众拓微信服务号',
    },

    'bidong' : {
        'grant_type':'client_credential',
        'appid':'wx3e09c0b3f5639426',
        'secret':'0b27f4decd12d953e673a88df03be427',
        'token':'bidongwifi110',
        'key':'ilnkivXX6EvB7kNF2A1R5dB0WsqPYqdVZHO39oT0jnT',
        'expire':7200,
        'note':'壁咚微信服务号-广州中国科学院计算机网络信息中心',
    },
        

}

import sys

sys.modules[__name__] = configure
