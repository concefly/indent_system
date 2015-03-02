# -*- coding:utf-8 -*-

import tornado.ioloop as tioloop
import tornado.web as tweb
import tornado.options as toptions
import tornado.auth as tauth
import tornado.httpserver as thttpserver
import tornado.escape as tescape

import datetime
import xml.etree.ElementTree as et
import pony.orm as orm

import sys
import os

pjoin = os.path.join

__dir__ = os.path.abspath(os.path.dirname(__file__))

toptions.define("port", default=8080, help="run on the given port", type=int)

# 配置数据库
db = orm.Database('sqlite', 'dev.sq3', create_db=True)

# 数据库 model
class User(db.Entity):
	id            = orm.PrimaryKey(int, auto=True)
	password      = orm.Optional(str)
	last_login    = orm.Required(datetime.datetime)
	user_type     = orm.Required(str)
	is_active     = orm.Required(bool)
	date_joined   = orm.Required(datetime.datetime)
	name          = orm.Optional(str)
	email         = orm.Optional(str)
	mobile        = orm.Optional(str)
	code          = orm.Optional(str, unique=True)
	balance       = orm.Required(float)
	# point         = orm.Required(float)
	point_member  = orm.Required(float)
	point_xzl     = orm.Required(float)
	point_jhs     = orm.Required(float)
	point_nlb     = orm.Required(float)
	point_nlt     = orm.Required(float)
	members       = orm.Set("User", reverse="parent_member")
	parent_member = orm.Optional("User", reverse="members")
	orders        = orm.Set("Log_order")
	funds_outlay  = orm.Set("Log_fund", reverse="fund_from")
	funds_income  = orm.Set("Log_fund", reverse="fund_to")
	point_outlay  = orm.Set("Log_point", reverse="point_from")
	point_income  = orm.Set("Log_point", reverse="point_to")


class Log_order(db.Entity):
	id              = orm.PrimaryKey(int, auto=True)
	user            = orm.Required(User)
	datetime        = orm.Required(datetime.datetime)
	is_verified     = orm.Required(bool)
	commodity_bills = orm.Set("Commodity_bill")


class Log_fund(db.Entity):
	id        = orm.PrimaryKey(int, auto=True)
	count     = orm.Required(float)
	datetime  = orm.Required(datetime.datetime)
	fund_from = orm.Required(User, reverse="funds_outlay")
	fund_to   = orm.Required(User, reverse="funds_income")


class Log_point(db.Entity):
	id         = orm.PrimaryKey(int, auto=True)
	count      = orm.Required(float)
	datetime   = orm.Required(datetime.datetime)
	point_from = orm.Optional(User, reverse="point_outlay")
	point_to   = orm.Required(User, reverse="point_income")


class Commodity(db.Entity):
	id          = orm.PrimaryKey(int, auto=True)
	price_sell  = orm.Required(float)
	price_stock = orm.Required(float)
	point       = orm.Required(float)
	count       = orm.Required(int)
	title       = orm.Optional(str)
	text        = orm.Optional(str)
	img         = orm.Optional(str)
	is_onsell   = orm.Required(bool)
	bills       = orm.Set("Commodity_bill")


class Commodity_bill(db.Entity):
	id        = orm.PrimaryKey(int, auto=True)
	count     = orm.Required(int)
	datetime  = orm.Required(datetime.datetime)
	log_order = orm.Required(Log_order)
	commodity = orm.Required(Commodity)


# sql_debug(True)
db.generate_mapping(create_tables=True)

class base_handler(tweb.RequestHandler):
	def get_current_user(self):
		user_json = self.get_secure_cookie("user_id")
		if not user_json:
			return None
		return tescape.json_decode(user_json)

	def get(self,*a,**ka):
		self.auth_get(*a,**ka)
	@tweb.authenticated
	def auth_get(self,*a,**ka):
		pass

	def post(self,*a,**ka):
		auth_post(*a,**ka)
	@tweb.authenticated
	def auth_post(self,*a,**ka):
		pass

	def write_xml(self,x):
		if isinstance(x,et.Element):
			x = et.tostring(x,encoding="utf-8")
		self.write(x)
		self.orm.set_header("Content-Type","text/xml")

class MainHandler(base_handler):
	def get(self):
		self.redirect("/auth/login")

class AuthLoginHandler(base_handler):
	def get(self):
		self.render(pjoin('auth','login.html'))

	def post(self):
		user_code = self.get_argument("user_code")
		with orm.db_session:
			this_user = User.get(code=user_code)
			if not this_user:
				self.redirect('/')
			user_id = this_user.id
			mode    = this_user.user_type
		# cookie 立即过期
		self.set_secure_cookie("user_id", tescape.json_encode(user_id), expires_days=None)
		if mode == "admin":
			self.redirect("/admin/task")
		else :
			self.redirect("/member/task")

class MemberTask(base_handler):
	def auth_get(self):
		this_user = [None]
		with orm.db_session:
			user_id = self.current_user
			this_user[0] = User[user_id]
		self.render(pjoin('member','task.html'), this_user=this_user[0])

class AdminTask(base_handler):
	def auth_get(self):
		this_user = [None]
		with orm.db_session:
			user_id = self.current_user
			this_user[0] = User[user_id]
		self.render(pjoin('admin','task.html'), this_user=this_user[0])

class Application(tweb.Application):
	def __init__(self):
		handlers = [
			(r"/member/task", MemberTask),
			(r"/admin/task", AdminTask),
			(r"/auth/login", AuthLoginHandler),
			# (r"/auth/logout", AuthLogoutHandler),
			(r"/", base_handler),
		]
		settings = dict(
				# blog_title    = u"Tornado Blog",
				template_path   = os.path.join(__dir__, "templates"),
				static_path     = os.path.join(__dir__, "static"),
				# ui_modules    = {"Entry": EntryModule},
				xsrf_cookies    = True,
				cookie_secret   = "E@NEIVcZ)26=JUQ,B0H0B6VvamU*Ks",
				login_url       = "/auth/login",
				debug           = True,
			)
		super(Application,self).__init__(handlers, **settings)

def main():
    toptions.parse_command_line()
    http_server = thttpserver.HTTPServer(Application())
    http_server.listen(8080)
    tioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()