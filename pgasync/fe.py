"""The frontend-exposed DB API 2.0 functions
"""
# System imports.
import random

# Sibling imports.
import protocol
from pool import PgPool
from format import format
from errors import *

# Twisted imports
from twisted.internet.defer import Deferred, maybeDeferred
from twisted.internet import reactor

# Required by the DB API 2.0
apilevel = "2.0"
paramstyle = "pyformat"
threadsafety = 1 # share the module, but not connections or cursors

_pools = {}

def connect(dbname,user,password="",host="127.0.0.1", port=5432, unicode=False, poolKey='__default__'):
	"""connect(dbname,user,password="",host="127.0.0.1", port=5432, unicode=False, poolKey='__default__' )

	Connect to the database.

	First two arguments, dbname and user, are required.
	"""
	if poolKey:
		c = (host,dbname,user,password,port,unicode,poolKey)

		try:
			pool = _pools[c]
		except:
			pool = PgPool(host,dbname,user,password,port,unicode,False)
			_pools[c] = pool

	else:
		pool = PgPool(host,dbname,user,password,port,unicode,True)

	return Connection(pool=pool,_libkey_=None)

class Transaction(object):
	def __init__(self,pool,connection):
		self._cursor = connection.cursor()
	
	def __getattr__(self,name):
		return self._cursor.__getattr__(name)

	def reopen(self):
		pass

class ConnectionPool(object):
	def __init__(self, libname, *args, **kwargs):
		assert libname == "pgasync", "This connection pool only supports pgasync"
		self.params = (args,kwargs)
		self.noisy = 1

	def __setattr__(self,name,val):
		if name == "max":
			c = self.connect()
			c._pool.max = val
		elif name == "min":
			c = self.connect()
			c._pool.min = val
		else:
			return object.__setattr__(self,name,val)

	def __getattr__(self,name):
		if name == "max":
			c = self.connect()
			return c._pool.max 
		if name == "min":
			c = self.connect()
			return c._pool.min 
		if name == "running":
			c = self.connect()
			return c._pool.running
		return object.__getattribute__(self,name)

	def connect(self):
		return connect(*self.params[0],**self.params[1])

	def runOperation(self, query, args={}):
		def errThrough(failure, next):
			next.errback(failure)

		conn = connect(*self.params[0],**self.params[1])
		cur = conn.cursor()
		d = Deferred()
		cur.execute(query, args).addErrback(errThrough, d)
		nd = conn.commit()
		nd.addCallback(lambda res, d: d.callback(res), d)
		nd.addErrback(errThrough, d)
		cur.release()
		return d

	def runQuery(self, query, args={}):
		conn = connect(*self.params[0],**self.params[1])
		cur = conn.cursor()
		d = cur.exFetch(query,args)
		cur.release()
		return d

	def runInteraction(self, fun, query, args={}):
		conn = connect(*self.params[0],**self.params[1])
		cur = conn.cursor()
		d = maybeDeferred(fun, cur, query, args)
		def commit(_, xconn, xcur):
			xconn.commit()
			xcur.release()
			return _
		d.addCallback(commit, conn, cur)
		return d

	def start(self):
		pass

	def close(self):
		pass

	def finalClose(self):
		pass

class Connection:
	"""A python DB API 2.0 compatible Connection object.
	"""
	def __init__(self,**kwargs):
		if not "_libkey_" in kwargs:
			raise ProgrammingError, "Connection object cannot be directly created.  Use connect()"
		self._factory = None
		self._pool = kwargs["pool"]
		self._cid = 0
		self._callbackQ = []
		self._intrans = 0
		self._errback = None
		self._cursor = None
		self._dirty = 0

	def addErrback(self,f,*args,**kwargs):
		self._errback = (f,args,kwargs)
		return self

	def cursor(self,**kwargs):
		"""cursor()

		Returns a new cursor object.
		"""
		if self._cursor:
			raise InterfaceError, "This connection already has a cursor associated with it"

		def setFactory(factory,_self=None):
			_self._factory = factory
			factory.conn = self
			_self._intrans = factory.pg.transStatus == protocol.PG_TRANS_IN and 1 or 0
			_self._cursor._flushStartQueue()

		self._cursor = Cursor(self,_libkey_=None)
		self._pool.get(setFactory,self,_self=self)

		return self._cursor

	def _fail(self,failure):
		self._pool.running -= 1
		if self._errback:
			f,a,kw = self._errback
			f(failure,*a,**kw)
		else:
			raise failure

	def commit(self,now=0):
		"""commit()

		DEFERRED

		Commit changes to the database in the current transaction.
		"""
		d = Deferred()

		self._callbackQ.append(d)

		self._cursor._query("COMMIT",self._callCallback,now)

		return d

	def rollback(self,now=0):
		"""rollback()

		DEFERRED

		Rollback changes to the database in the current transaction.  The
		changes will not permanently apply to the database, and a new 
		transaction will be started.
		"""
		d = Deferred()

		self._callbackQ.append(d)

		self._cursor._query("ROLLBACK",self._callCallback,now)

		return d

	def _callCallback(self):
		"""Pop a callback out of the queue and call it.
		"""
		if self._factory:
			pg = self._factory.pg

			if pg.failure:
				d = self._callbackQ.pop(0)
				d.errback(pg.failure)
				pg.disconnect()
				self._pool.running -= 1
				self._pool.pool.remove(self._factory)
				self._factory = None
				return

		self._intrans = 0
		self._dirty = 0
		d = self._callbackQ.pop(0)
		d.callback(None)
		
	def close(self):
		"""close()

		Close the connection to the database.
		"""
		if self._cursor:
			self._cursor.release()

	def _curId(self):
		self._cid += 1
		return self._cid

	def exFetch(self,query,params=None):
		"""exFetch(query,{"param1" : value1,["param2" : value2,...]})

		DEFERRED argument 1 is a list of row(s) fetched

		Execute a query with he given parameters properly formatted.  
		Fetch the result, and pass that to the callback.

		The parameter style is 'pyparam,' which uses a syntax like the 
		following:

		cursor.exFetch("SELECT * FROM PEOPLE WHERE name = %{name}s and age = %{age}s",{"name":"Joe",'age':29})
		"""
		conn = Connection(pool=self._pool,_libkey_=None)
		cur = conn.cursor()
		d = cur.exFetch(query,params)
		cur.release()

		return d


class Cursor:
	"""A python DB API 2.0 compatible Cursor object.
	"""
	def __init__(self,conn,**kwargs):
		if not "_libkey_" in kwargs:
			raise ProgrammingError, "Cursor object cannot be directly created.  Use Connection.cursor()"
		self.description = None
		self.rowcount = -1
		self.arraysize = 1
		self.connection = conn
		self._callbackQ = []
		self._cid = None
		self._startQ = []
		self._startReleased = 0

	def _genCid(self):
		return "c%d%d" % (random.randint(1000000,9999999), self.connection._curId())

	def _query(self,*args,**kwargs):
		if self.connection._factory:
			if not self.connection._intrans:
				self.connection._intrans = 1
				self._callin("BEGIN")
			self._callin(*args,**kwargs)
		else:
			self._startQ.append((args,kwargs))

	def _flushStartQueue(self):
		self._callin = self.connection._factory.pg.callin_query
		if not self.connection._intrans:
			self.connection._intrans = 1
			if self.connection._factory.unicode:
				self._callin("SET client_encoding = 'utf-8'")
			self._callin("BEGIN")
		for args,kw in self._startQ:
			self._callin(*args,**kw)
		if self._startReleased:
			self.connection._factory.pg.callbackQ.append(protocol.ContinuingCallback(self._release))

	def close(self):
		"""close()

		Close the connection to the database.
		"""
		self.connection._factory.pg.disconnect()
		self.connection._pool.running -= 1
		try:
			self.connection._pool.pool.remove(self.connection._factory)
		except:
			pass
		self.connection._factory = None
		self.connection._cursor = None
		self.connection = None

	def release(self):
		if not self.connection._factory:
			self._startReleased = 1
		elif self.connection._factory.pg.callbackQ:
			self.connection._factory.pg.callbackQ.append(protocol.ContinuingCallback(self._release))
		else:
			self._release()
		
	def _release(self,dc=None):
		"""
		Make sure that we rollback any changes when the cursor is done.

		We don't want hanging transactions on persistent connections.
		"""
		conn = self.connection
		if not conn:
			return # already been released

		conn._cursor = None

		if conn._factory:
			if conn._pool._once:
				conn._factory.pg.disconnect()
			f = conn._factory
			if f.conn:
				f.conn = None
			conn._factory = None
			conn._intrans = 0
			if conn._dirty:
				f.pg.callin_query("ROLLBACK")
				conn._dirty = 0
			conn._pool.add(f)
		

		self.connection = None

	def execute(self,query,params=None):
		"""execute(query,{"param1" : value1,["param2" : value2,...]})

		DEFERRED

		Execute a query with he given parameters properly formatted.

		The parameter style is 'pyparam,' which uses a syntax like the 
		following:

		cursor.execute("SELECT * FROM PEOPLE WHERE name = %{name}s and age = %{age}s",{"name":"Joe",'age':29})
		"""
		d = Deferred()

		if not self.connection:
			reactor.callLater(0,d.errback,
			OperationalError("Cannot execute query: the connection has been closed"))
			return d

		self.description = None
		self.rowcount = -1


		self._callbackQ.append(d)

		s = format(query,params)

		if self._cid:
			self._query("CLOSE %s" % self._cid)
			self._cid = None

		if s[:7].upper() == "SELECT ":
			self._cid = self._genCid()
			s = "DECLARE %s CURSOR FOR (%s)" % (self._cid,s)
		else:
			self.connection._dirty = 1 # they have executed things other than SELECT

		self._query(s,self._done_execute)

		return d

	def _done_execute(self):
		"""Called when execution is done in protocol.py.
		"""

		# check for error
		pg = self.connection._factory.pg

		if pg.failure:
			d = self._callbackQ.pop(0)
			d.errback(pg.failure)
			self.close()
			return

		self.rowcount = self.connection._factory.pg.rowcount

		d = self._callbackQ.pop(0)
		d.callback(None)

	def fetchone(self,num=-1):
		"""fetchone()

		DEFERRED: argument 1 is a list of the row fetched

		Fetches a single row from the result set obtained by executing 
		the previous query.
		"""

		d = Deferred()

		if not self.connection:
			reactor.callLater(0,d.errback,
			OperationalError("Cannot execute query: the connection has been closed"))
			return d

		self._callbackQ.append(d)

		if num <= 0:
			self._query("FETCH NEXT FROM %s" % self._cid,self._done_fetch_one)
		else:
			self._query("FETCH ABSOLUTE %d FROM %s" % (num,self._cid),self._done_fetch_one)

		return d
	
	def _done_fetch_one(self):
		# check for error
		pg = self.connection._factory.pg

		if pg.failure:
			d = self._callbackQ.pop(0)
			d.errback(pg.failure)
			self.close()
			return

		self.rowcount = len(pg.rows)
		self.description = pg.curfields
		d = self._callbackQ.pop(0)

		if self.rowcount:
			d.callback(pg.rows[0])
		else:
			d.callback(None)

	def fetchmany(self,size=None):
		"""fetchmany(size=arraysize)

		DEFERRED: argument 1 is a list the row(s) fetched

		Fetches multiple rows from the result set obtained by the previous query.

		Uses self.arraysize if no number of rows is specfied.
		"""
		if not size:
			size = self.arraysize

		d = Deferred()

		if not self.connection:
			reactor.callLater(0,d.errback,
			OperationalError("Cannot execute query: the connection has been closed"))
			return d

		self._callbackQ.append(d)

		self._query("FETCH FORWARD %d FROM %s" % (size,self._cid),self._done_fetch)

		return d

	def fetchall(self):
		"""fetchall()

		DEFERRED: argument 1 is a list the row(s) fetched

		Fetches all remaining rows from the result set obtained by the 
		previous query.
		"""
		d = Deferred()

		if not self.connection:
			reactor.callLater(0,d.errback,
			OperationalError("Cannot execute query: the connection has been closed"))
			return d

		self._callbackQ.append(d)

		self._query("FETCH FORWARD ALL FROM %s" % (self._cid),self._done_fetch)

		return d

	def _done_fetch(self):
		# check for error
		pg = self.connection._factory.pg

		if pg.failure:
			d = self._callbackQ.pop(0)
			d.errback(pg.failure)
			self.close()
			return

		self.description = pg.curfields
		self.rowcount = len(pg.rows)
		d = self._callbackQ.pop(0)
		d.callback(pg.rows)

	
	def _errThrough(failure, next):
		next[0].errback(failure)
	_errThrough = staticmethod(_errThrough)

	def exFetch(self,query,params=None):
		"""exFetch(query,{"param1" : value1,["param2" : value2,...]})

		DEFERRED argument 1 is a list of row(s) fetched

		Execute a query with he given parameters properly formatted.  
		Fetch the result, and pass that to the callback.

		The parameter style is 'pyparam,' which uses a syntax like the 
		following:

		cursor.exFetch("SELECT * FROM PEOPLE WHERE name = %{name}s and age = %{age}s",{"name":"Joe",'age':29})
		"""
		v = []
		self.execute(query,params).addErrback(self._errThrough, v)
		d = self.fetchall()
		v.append(d)
		return d

	def setinputsizes(v):
		"""setinputsizes(size)

		Does nothing in this implementation.
		"""
		pass

	def setoutputsize(v):
		"""setoutputsize(size)

		Does nothing in this implementation.
		"""
		pass
