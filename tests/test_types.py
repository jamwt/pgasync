from testbase import *
import pgasync
from twisted.internet.defer import waitForDeferred as waitD, deferredGenerator

class TestNone(TestCase):
	schema = 'id int, nil varchar(1)'

	@deferredGenerator
	def testnull(self):
		id = getId()
		i = None
		
		yield waitD(self.pool.runOperation(
		'insert into t_tbl VALUES(%d, %s)',(id, i,)))
		
		d = waitD(
		self.pool.runQuery(
		'select nil from t_tbl where id = %d', (id,))
		)
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])

class TestIntegers(TestCase):
	schema = 'id int, t_smallint smallint, t_int int, t_bigint bigint'

	@deferredGenerator
	def test_smallint(self):
		id = getId()
		i = 8

		yield waitD(
		self.pool.runOperation(
		'insert into t_tbl VALUES(%d, %d, NULL, NULL)',(id, i,)))
		
		d = waitD(
		self.pool.runQuery(
		'select t_smallint from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])

	@deferredGenerator
	def test_int(self):
		id = getId()
		i = 66666
		
		yield waitD(
		self.pool.runOperation(
		'insert into t_tbl VALUES(%d, NULL, %d, NULL)',(id, i,)))
		
		d = waitD(
		self.pool.runQuery(
		'select t_int from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])

	@deferredGenerator
	def test_bigint(self):
		id = getId()
		i = 6000000000

		yield waitD(
		self.pool.runOperation(
		'insert into t_tbl VALUES(%d, NULL, NULL, %d)',(id, i,)))
		
		d = waitD(
		self.pool.runQuery(
		'select t_bigint from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])

from decimal import Decimal
class TestFloats(TestCase):
	schema = 'id int, t_numeric numeric, t_real real, t_dp double precision'

	@deferredGenerator
	def test_numeric(self):
		id = getId()
		i = Decimal('3.291283719')

		yield waitD(
		self.pool.runOperation(
		'insert into t_tbl VALUES(%d, %s, NULL, NULL)',(id, i,)))
		
		d = waitD(
		self.pool.runQuery(
		'select t_numeric from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])

	@deferredGenerator
	def test_real(self):
		id = getId()
		i = 3.291283719
		ti = type(i)

		yield waitD(
		self.pool.runOperation(
		'insert into t_tbl VALUES(%d, NULL, %s, NULL)',(id, i,)))
		
		d = waitD(
		self.pool.runQuery(
		'select t_real from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(ti, type(o[0][0]))

	@deferredGenerator
	def test_double(self):
		id = getId()
		i = 3.291283719
		ti = type(i)

		yield waitD(
		self.pool.runOperation(
		'insert into t_tbl VALUES(%d, NULL, NULL, %s)',(id, i,)))
		
		d = waitD(
		self.pool.runQuery(
		'select t_dp from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(ti, type(o[0][0]))

class TestMoney(TestCase):
	schema = 'id int, t_money money'

	@deferredGenerator
	def test_money(self):
		id = getId()
		i = Decimal('3.29')

		yield waitD(self.pool.runOperation(
		'insert into t_tbl VALUES(%d, %s)',(id, pgasync.MONEY(i))))
		
		d = waitD(
		self.pool.runQuery(
		'select t_money from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])

class TestStrings(TestCase):
	schema = 'id int, t_varchar varchar(30), t_char char(5), t_text text, t_bytea bytea'

	@deferredGenerator
	def test_varchar(self):
		id = getId()
		i = "how's she doing; good)?'"

		yield waitD(
		self.pool.runOperation(
		'insert into t_tbl VALUES(%d, %s, NULL, NULL, NULL)',(id, i,)))
		
		d = waitD(self.pool.runQuery(
		'select t_varchar from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])


	@deferredGenerator
	def test_char(self):
		id = getId()
		i = "'wh\\"
	
		yield waitD(self.pool.runOperation(
		'insert into t_tbl VALUES(%d, NULL, %s, NULL, NULL)',(id, i,)))
		
		d = waitD(self.pool.runQuery(
		'select t_char from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i + (' ' * (5 - len(i))), o[0][0])

	@deferredGenerator
	def test_text(self):
		id = getId()
		i = "how's s\x13he doing; good)?'" 

		yield waitD(self.pool.runOperation(
		'insert into t_tbl VALUES(%d, NULL, NULL, %s, NULL)',(id, i,)))
		
		d = waitD(self.pool.runQuery(
		'select t_text from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])

	@deferredGenerator
	def test_bytea(self):
		id = getId()

		import random
		i = ''.join([chr(random.randint(0,255)) for x in range(100 * 1024)])

		yield waitD(self.pool.runOperation(
		'insert into t_tbl VALUES(%d, NULL, NULL, NULL, %s)',(id, pgasync.BINARY(i),)))
		
		d = waitD(self.pool.runQuery(
		'select t_bytea from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])

import datetime
class TestDatesTimes(TestCase):
	schema = 'id int, t_date date, t_time time, t_timestamp timestamp'

	@deferredGenerator
	def test_date(self):
		id = getId()
		i = datetime.date(1980, 12, 28)

		yield waitD(self.pool.runOperation(
		'insert into t_tbl VALUES(%d, %s, NULL, NULL)',(id, i,)))
		
		d = waitD(self.pool.runQuery(
		'select t_date from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])

	@deferredGenerator
	def test_time(self):
		id = getId()
		i = datetime.time(8,8,0,234)
		o = [None]
		yield waitD(self.pool.runOperation(
		'insert into t_tbl VALUES(%d, NULL, %s, NULL)',(id, i,)))
		
		d = waitD(self.pool.runQuery(
		'select t_time from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])

	@deferredGenerator
	def test_timestamp(self):
		id = getId()
		i = datetime.datetime(1980, 12, 28, 8, 8, 0, 234)
		o = [None]
		yield waitD(self.pool.runOperation(
		'insert into t_tbl VALUES(%d, NULL, NULL, %s)',(id, i,)))
		
		d = waitD(self.pool.runQuery(
		'select t_timestamp from t_tbl where id = %d', (id,)))
		yield d
		o = d.getResult()

		self.assertEquals(i, o[0][0])
