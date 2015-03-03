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
	last_login    = orm.Optional(datetime.datetime)
	user_type     = orm.Optional(str, default='member')
	is_active     = orm.Optional(bool, default=True)
	date_joined   = orm.Optional(datetime.datetime)
	name          = orm.Optional(str)
	email         = orm.Optional(str)
	mobile        = orm.Optional(str)
	address       = orm.Optional(str)
	code          = orm.Optional(str, unique=True)
	balance       = orm.Optional(float, default=0)
	point_total   = orm.Optional(float, default=0)
	point_member  = orm.Optional(float, default=0)
	point_xzl     = orm.Optional(float, default=0)
	point_jhs     = orm.Optional(float, default=0)
	point_nlb     = orm.Optional(float, default=0)
	point_nlt     = orm.Optional(float, default=0)
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
	datetime        = orm.Optional(datetime.datetime)
	is_verified     = orm.Optional(bool, default=False)
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
	price_sell  = orm.Optional(float, default=0)
	price_stock = orm.Optional(float, default=0)
	point       = orm.Optional(float, default=0)
	count       = orm.Optional(int, default=0)
	title       = orm.Optional(str)
	text        = orm.Optional(str)
	img         = orm.Optional(str)
	is_onsell   = orm.Optional(bool, default=True)
	bills       = orm.Set("Commodity_bill")


class Commodity_bill(db.Entity):
	id        = orm.PrimaryKey(int, auto=True)
	count     = orm.Required(int)
	datetime  = orm.Optional(datetime.datetime)
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
		self.auth_post(*a,**ka)
	@tweb.authenticated
	def auth_post(self,*a,**ka):
		pass

	def write_xml(self,x):
		if isinstance(x,et.Element):
			x = et.tostring(x,encoding="utf-8")
		self.write(x)
		self.set_header("Content-Type","text/xml")

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

class AuthLogoutHandler(base_handler):
	def get(self):
		self.clear_cookie("user_id")
		self.redirect(self.get_argument("next", "/"))

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

class AppendInitialMember(base_handler):
	def auth_get(self):
		self.render(pjoin('admin','append_initial_member.html'))
	def auth_post(self):
		user_code = self.get_body_argument("user_code")
		with orm.db_session:
			if User.get(code=user_code):
				self.write("User already exist")
				return
			new_user = User(
				code         = user_code,
				last_login   = datetime.datetime.now(),
				user_type    = 'member',
				is_active    = True,
				date_joined  = datetime.datetime.now(),
				balance      = 0,
				point_member = 0,
				point_jhs    = 0,
				point_xzl    = 0,
				point_nlt    = 0,
				point_nlb    = 0)
		self.render(pjoin('admin','operate_ok.html'))

class AppendNormalMember(base_handler):
	def auth_get(self):
		self.render(pjoin('admin','append_normal_member.html'))
	def auth_post(self):
		parent_member = self.get_body_argument("parent_member")
		user_code     = self.get_body_argument("user_code")
		name          = self.get_body_argument("name")
		password      = self.get_body_argument("password")
		mobile        = self.get_body_argument("mobile")
		address       = self.get_body_argument("address")
		email         = self.get_body_argument("email")
		with orm.db_session:
			if User.get(code=user_code):
				self.write("User already exist")
				return
			if not User.get(code=parent_member):
				self.write("Parent not exist")
				return
			new_user = User(
				parent_member = User.get(code=parent_member),
				code         = user_code,
				last_login   = datetime.datetime.now(),
				user_type    = 'member',
				is_active    = True,
				date_joined  = datetime.datetime.now(),
				balance      = 0,
				point_member = 0,
				point_jhs    = 0,
				point_xzl    = 0,
				point_nlt    = 0,
				point_nlb    = 0,
				name         = name,
				password     = password,
				mobile       = mobile,
				address      = address,
				email        = email)
		self.render(pjoin('admin','operate_ok.html'))

class MemberList(base_handler):
	def auth_get(self):
		self.render(pjoin('admin','member_list.html'))

class DataMembers(base_handler):
	user_field = [
		# (field name, (models...))
		("user_code",("code",)),
		("date_joined",('date_joined',)),
		("parent_member",('parent_member','code')),
		("balance",('balance',)),
		("point_member",('point_member',)),
		("point_xzl",('point_xzl',)),
		("point_jhs",('point_jhs',)),
		("point_nlb",('point_nlb',)),
		("point_nlt",('point_nlt',)),]
	post_field = [
		# (field name, (models...))
		("balance",('balance',)),
		("point_member",('point_member',)),
		("point_xzl",('point_xzl',)),
		("point_jhs",('point_jhs',)),
		("point_nlb",('point_nlb',)),
		("point_nlt",('point_nlt',)),]
	default_frame = os.path.join(__dir__,"static","frame","member_default.xml")
	def auth_get(self):
		if hasattr(self,"default_frame"):
			rows = et.parse(self.default_frame).getroot()
		else:
			rows = et.Element('rows')
		with orm.db_session:
			query = User.select()
			for n,this_user in enumerate(query):
				row = et.Element("row")
				row.set("id",str(this_user.id))
				# 填充序号
				cell = et.Element("cell")
				cell.text = str(n+1)
				row.append(cell)
				# 填充字段
				for name,models in self.user_field:
					cell = et.Element("cell")
					try:
						cell.text = str(eval("this_user.%s" %(".".join(models),)))
					except AttributeError:
						cell.text = '-'
					# cell.text = str(reduce(lambda x,y:getattr(x,y), models, this_user))
					row.append(cell)
				# 
				rows.append(row)
		self.write_xml(rows)
	def auth_post(self):
		if self.get_argument("editing",default=None) != "true":
			return
		ids = self.get_body_argument("ids",default="").split(',')
		res = et.Element("data")
		for _id in ids:
			gr_id = self.get_body_argument("%s_gr_id" %(_id,))
			field = {}
			# 获取POST参数
			for name,models in self.post_field:
				field[name] = self.get_body_argument("%s_%s" %(_id,name))
			status = self.get_body_argument("%s_!nativeeditor_status" %(_id,))
			# 写入数据库
			tid = [gr_id]
			with orm.db_session:
				if status=="updated":
					this_user = User[gr_id]
					for name,models in self.post_field:
						_model = reduce(lambda x,y:getattr(x,y), models[:-1], this_user)
						setattr(_model,models[-1],field[name])
				if status=="inserted":
					init_field = dict(field)
					this_user = User(**init_field)
					# 提交以更新id
					orm.commit()
					tid[0] = str(r.id)
				if status=="deleted":
					this_user = User[gr_id]
					User[gr_id].delete()
			# 插入一条 action xml item
			act = et.Element("action")
			act.set("type",status)
			act.set("sid",gr_id)
			act.set("tid",tid[0])
			res.append(act)
		self.write_xml(res)

class CommodityManager(base_handler):
	def auth_get(self):
		self.render(pjoin('admin','commodity_manager.html'))

class DataCommodities(base_handler):
	model = Commodity
	user_field = [
		# (field name, (models...))
		('title'       ,('title',)),
		('img'         ,('img',)),
		('price_sell'  ,('price_sell',)),
		('price_stock' ,('price_stock',)),
		('count'       ,('count',)),
		('point'       ,('point',)),
		('text'        ,('text',)),
		('is_onsell'   ,('is_onsell',)),]
	post_field_processor = {
		"is_onsell" : lambda x: True if x=='True' else False,
	}
	post_field = user_field
	default_frame = os.path.join(__dir__,"static","frame","commodity_grid_default.xml")
	def auth_get(self):
		if hasattr(self,"default_frame"):
			rows = et.parse(self.default_frame).getroot()
		else:
			rows = et.Element('rows')
		with orm.db_session:
			query = self.model.select()
			for n,this_user in enumerate(query):
				row = et.Element("row")
				row.set("id",str(this_user.id))
				# 填充序号
				cell = et.Element("cell")
				cell.text = str(n+1)
				row.append(cell)
				# 填充字段
				for name,models in self.user_field:
					cell = et.Element("cell")
					try:
						value = eval("this_user.%s" %(".".join(models),))
						cell.text = str(value)
						if hasattr(self,'user_field_processor'):
							if self.user_field_processor.has_key(name):
								cell.text = self.user_field_processor[name](value)
					except AttributeError:
						cell.text = '-'
					row.append(cell)
				# 
				rows.append(row)
		self.write_xml(rows)
	def auth_post(self):
		if self.get_argument("editing",default=None) != "true":
			return
		ids = self.get_body_argument("ids",default="").split(',')
		res = et.Element("data")
		for _id in ids:
			gr_id = self.get_body_argument("%s_gr_id" %(_id,))
			field = {}
			# 获取POST参数
			for name,models in self.post_field:
				field[name] = self.get_body_argument("%s_%s" %(_id,name))
			status = self.get_body_argument("%s_!nativeeditor_status" %(_id,))
			# 写入数据库
			tid = [gr_id]
			with orm.db_session:
				if status=="updated":
					this_user = self.model[gr_id]
					for name,models in self.post_field:
						_model = reduce(lambda x,y:getattr(x,y), models[:-1], this_user)
						if hasattr(self,"post_field_processor"):
							if self.post_field_processor.has_key(name):
								field[name] = self.post_field_processor[name](field[name])
						setattr(_model,models[-1],field[name])
				if status=="inserted":
					init_field = dict(field)
					this_user = self.model(**init_field)
					# 提交以更新id
					orm.commit()
					tid[0] = str(this_user.id)
				if status=="deleted":
					this_user = self.model[gr_id]
					self.model[gr_id].delete()
			# 插入一条 action xml item
			act = et.Element("action")
			act.set("type",status)
			act.set("sid",gr_id)
			act.set("tid",tid[0])
			res.append(act)
		self.write_xml(res)

class MemberShop(base_handler):
	@orm.db_session
	def auth_get(self):
		self.render(pjoin('member','shop.html'),Commodity=Commodity)

class MemberPlaceOrder(base_handler):
	def auth_get(self):
		self.redirect("/member/shop")
	@orm.db_session
	def auth_post(self):
		try:
			commodity_id = int(self.get_body_argument("commodity_id"))
			count        = int(self.get_body_argument("count"))
			# TODO: 检查库存和余额
			this_order = Log_order(
				user        = User[self.current_user],
				datetime    = datetime.datetime.now(),
				is_verified = False,)
			this_bill = Commodity_bill(
				count     = count,
				datetime  = datetime.datetime.now(),
				log_order = this_order,
				commodity = Commodity[commodity_id])
			this_order.commodity_bills.add(this_bill)
			self.render(pjoin('member','operate_ok.html'))
		except:
			raise

class DataHistoryOrder(DataCommodities):
	model = Log_order
	user_field = [
		# (field name, (models...))
		('order_code'  ,('id',)),
		('datetime'    ,('datetime',)),
		('verified'    ,('is_verified',)),
		('commodities' ,('commodity_bills',))]
	def commodities_processor(bills):
		s = ['']
		for bill in bills:
			s[0] += '%s:%s ' %(bill.commodity.title, bill.count)
		return s[0]
	user_field_processor = {
		'verified'    : lambda x: "True" if x else "False",
		'commodities' : commodities_processor,
	}
	default_frame = os.path.join(__dir__,"static","frame","history_order_grid_default.xml")
	def auth_post(self):
		pass

class MemberHistoryOrder(base_handler):
	def auth_get(self):
		self.render(pjoin('member','history_order.html'))

class MemberRegisterMember(base_handler):
	def auth_get(self):
		self.render(pjoin('member','register_member.html'))
	@orm.db_session
	def auth_post(self):
		name          = self.get_body_argument("name")
		password      = self.get_body_argument("password")
		mobile        = self.get_body_argument("mobile")
		address       = self.get_body_argument("address")
		email         = self.get_body_argument("email")
		new_user = User(
			parent_member = User[self.current_user],
			last_login    = datetime.datetime.now(),
			user_type     = 'member',
			is_active     = True,
			date_joined   = datetime.datetime.now(),
			balance       = 0,
			point_member  = 0,
			point_jhs     = 0,
			point_xzl     = 0,
			point_nlt     = 0,
			point_nlb     = 0,
			name          = name,
			password      = password,
			mobile        = mobile,
			address       = address,
			email         = email)
		self.render(pjoin('member','operate_ok.html'))

class MemberPointTransfer(base_handler):
	@orm.db_session
	def auth_get(self):
		self.render(pjoin('member','point_transfer.html'),
			Log_point=Log_point,
			this_user=User[self.current_user])
	def auth_post(self):
		target_code    = self.get_body_argument('target_code')
		transfer_point = self.get_body_argument('transfer_point')
		with orm.db_session:
			target_user = User.get(code=target_code)
			source_user = User[self.current_user]
			if not target_user or not source_user:
				self.redirect('/member/point_transfer')
				return
			# TODO 积分验证
			target_user.point_total += transfer_point
			source_user.point_total -= transfer_point
		self.render('member','operate_ok.html')

class Application(tweb.Application):
	def __init__(self):
		handlers = [
			# data
			(r"/data/members"       , DataMembers),
			(r"/data/history_order" , DataHistoryOrder),
			(r"/data/commodities"   , DataCommodities),
			# member
			(r"/member/shop"          , MemberShop),
			(r"/member/history_order" , MemberHistoryOrder),
			(r"/member/point_transfer" , MemberPointTransfer),
			(r"/member/register_member" , MemberRegisterMember),
			(r"/member/place_order"   , MemberPlaceOrder),
			(r"/member/task"          , MemberTask),
			# admin
			(r"/admin/append_initial_member" , AppendInitialMember),
			(r"/admin/append_normal_member"  , AppendNormalMember),
			(r"/admin/member_list"           , MemberList),
			(r"/admin/commodity_manager"     , CommodityManager),
			(r"/admin/task"                  , AdminTask),
			# auth
			(r"/auth/login"  , AuthLoginHandler),
			(r"/auth/logout" , AuthLogoutHandler),
			(r"/"            , base_handler),
		]
		settings = dict(
				# blog_title    = u"Tornado Blog",
				template_path   = os.path.join(__dir__, "templates"),
				static_path     = os.path.join(__dir__, "static"),
				# ui_modules    = {"Entry": EntryModule},
				xsrf_cookies    = False,
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