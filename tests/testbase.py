import sys
import pgasync
import unittest

DATABASE = dict(dbname='pgasync_testdb', user='pgasync_testuser', password='pgasync_testpass')

DB_ONCE = DATABASE.copy()
DB_ONCE['poolKey'] = None

def getSuccessfulPool():
	return pgasync.ConnectionPool('pgasync',**DB_ONCE)

def idGetter():
	x = 1
	while 1:
		yield x
		x += 1

getId = idGetter().next

class TestCase(unittest.TestCase):
	def setUp(self):
		self.pool = getSuccessfulPool()
		return self.pool.runOperation(
		'create table t_tbl (%s)' % self.schema)

	def tearDown(self):
		return self.pool.runOperation('drop table t_tbl').addCallback(
		lambda r, self: self.pool.connect().close(), self)
