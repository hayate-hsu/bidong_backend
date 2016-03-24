#!/usr/bin/env python
#coding:utf-8
menu = {
	'button':[
	{
		'type':'view',
		'name':'一键上网',
		'url':'https://open.weixin.qq.com/connect/oauth2/authorize?appid=wxa7c14e6853105a84&redirect_uri=http%3A%2F%2Fmbd.cniotroot.cn%2Fwx%2Fm_bidong%2Fonetonet&response_type=code&scope=snsapi_base#wechat_redirect',
	},
	{
		'type':'view',
		'name':'赚咚币',
		'url':'https://open.weixin.qq.com/connect/oauth2/authorize?appid=wxa7c14e6853105a84&redirect_uri=http%3A%2F%2Fmbd.cniotroot.cn%2Fwx%2Fm_bidong%2Fearn_coin&response_type=code&scope=snsapi_base#wechat_redirect',
	},
	{
		'type':'view',
		'name':'我要壁咚',
		'url':'https://open.weixin.qq.com/connect/oauth2/authorize?appid=wxa7c14e6853105a84&redirect_uri=http%3A%2F%2Fmbd.cniotroot.cn%2Fwx%2Fm_bidong%2Fjoin_us&response_type=code&scope=snsapi_base#wechat_redirect'
	},
	],
}

sys.modules[__name__] = json_encoder(menu)
