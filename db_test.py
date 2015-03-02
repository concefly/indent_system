# -*- coding:utf-8 -*-

import datetime
import xml.etree.ElementTree as et
import pony.orm as orm

import sys
import os

pjoin = os.path.join
__dir__ = os.path.abspath(os.path.dirname(__file__))
sys.path.append(__dir__)

from server import *

dat = dict(
	code          = 'concefly',
	last_login    = datetime.datetime.now(),
	user_type     = 'admin',
	is_active     = True,
	date_joined   = datetime.datetime.now(),
	balance       = 10000,
	point_member  = 10000,
	point_xzl     = 10000,
	point_jhs     = 10000,
	point_nlb     = 10000,
	point_nlt     = 10000
	)

with orm.db_session:
	User(**dat)
