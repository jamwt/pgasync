"""Connection pooling.
"""

# System imports
import time

# Twisted imports
from twisted.internet import reactor

# Sibling imports
from protocol import PgFactory

PG_CONNECTION_TIMEOUT = 30
PG_POOL_PRUNE = 11

try:
	import gc
except ImportError:
	gc = None

PG_POOL_MAX = 20
PG_POOL_MIN = 0

class PgPool:
	"""Implement a connection pool that prunes unused connections.

	Connection, in this layer is a PgFactory.
	"""
	def __init__(self,host,dbname,user,password,port,unicode,once):
		self.host = host
		self.dbname = dbname
		self.user = user
		self.password = password
		self.port = port
		self.unicode = unicode

		self.max = PG_POOL_MAX
		self.min = PG_POOL_MIN
		self.running = 0
		self._once = once

		self.pool = []
		self.waitingFuncs = []
		if not once:
			reactor.callLater(PG_POOL_PRUNE,self.prune)

	def get(self,cb,conn,**kwargs):
		"""Return a factory from the pool.

		Create it if it's not already there.
		"""
		if len(self.pool):
			f, ts = self.pool.pop()
			f.conn = conn
			cb(f,**kwargs)
		else:		
			if self._once or self.max < 0 or self.running < self.max:
				f = PgFactory(self, self.host,self.dbname, self.user, self.password,self.port,self.unicode,conn)

				if self.host[0]=='/':
					host = self.host + ("/.s.PGSQL.%d" % self.port)
					reactor.connectUNIX(host,f)
				else:
					reactor.connectTCP(self.host,self.port,f)

				self.running += 1
			self.waitingFuncs.append((cb,kwargs))
		
	def add(self,f):
		"""Add a factory back into the pool.
		"""
		if len(self.waitingFuncs):
			cb,kwargs = self.waitingFuncs.pop(0)
			cb(f,**kwargs)
		elif not self._once:
			self.pool.append((f,time.time()))

	def prune(self):
		"""Prune idle PgFactory instances from the pool.

		Drops ones unused for PG_CONNECTION_TIMEOUT; checks every
		PG_POOL_PRUNE.
		"""
		t = time.time()
		x = 0
		y = len(self.pool)
		while self.running > self.min and x < y:
			if t - self.pool[x][1] > PG_CONNECTION_TIMEOUT:
				self.pool[x][0].pg.disconnect()
				self.running -= 1
				del self.pool[x]
				y -= 1
			else:
				x += 1

		if gc:
			gc.collect()
		reactor.callLater(PG_POOL_PRUNE,self.prune)
