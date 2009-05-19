"""Protocol implementation, built on net.py and the twisted reactor core.
"""
# System Imports
from struct import *
import md5
try:
	import cStringIO as StringIO
except:
	import StringIO

# Twisted Imports
from twisted.internet.protocol import ClientFactory
from twisted.python import log

# Sibling Imports
from net import CountTerminatedProtocol
from errors import *
from cache import Cache
import registry

PG_VERSION_MAJOR = 3
PG_VERSION_MINOR = 0

PG_PROTO_VERSION = (PG_VERSION_MAJOR << 16) | PG_VERSION_MINOR 

PG_TRANS_IDLE, PG_TRANS_IN, PG_TRANS_ERROR = range(3)

PG_TRANS_MAP = {
	"I" : PG_TRANS_IDLE, 
	"T" : PG_TRANS_IN,
	"E" : PG_TRANS_ERROR,
}

class ContinuingCallback:
	def __init__(self,func):
		self.func = func

class PgProtocol(CountTerminatedProtocol):
	"""Implements the frontend side of the PostgreSQL Database Server,
	protocol version 3.0.
	"""


	def __init__(self):
		CountTerminatedProtocol.__init__(self,5)  
		self.terminatedDataReceived = self.packetSwitch

		self.datacache = Cache()


		# The first byte of each pg packet we get from the server, 
		# we switch on this is self.packetSwitch().
		self.packetMethods = {
			"E" : self.packet_error,             # Error
			"N" : self.packet_notice,            # Notice

			"R" : self.packet_auth,              # Authentication 
			"S" : self.packet_param,             # Backend Parameters
			"K" : self.packet_cancel,            # Cancellation Key

			"T" : self.packet_fields,            # Field Descriptions
			"D" : self.packet_data,              # Row data
			"c" : self.packet_datadone,          # Rows all sent
			"C" : self.packet_cmddone,           # Last executed command is complete

			"Z" : self.packet_ready,             # Ready for Query
		}

		# Currently supported authentication methods.
		self.authMethods = {
			0 : self.auth_ok,        # Ok -- we're in
			3 : self.auth_pass,      # Cleartext Password
			5 : self.auth_md5,       # MD5 Password
		}

		self.auth = 0

		# The parameters the backend gives us about its run environment.
		self.params = {}

		self.transStatus = PG_TRANS_IDLE

		self.callbackQ = [] # <-- We stack callbacks to fe.py here.
		self.queryQ = [] # <-- We stack queries here
		self.inquery = 0  # <-- currently in query

		self.failure = None

	def switch(self):
		"""After handling a specific packet, go back to regular switching.
		"""
		self.terminator = 5
		self.terminatedDataReceived = self.packetSwitch

	def connectionMade(self):
		'''Send our startup packet.
		'''

		db = self.factory.dbname + "\0\0" # last param
		ldb = len(db)
		user = self.factory.user + "\0"
		luser = len(user)

		l = ldb + luser + 22  # (4 + 4 + 5 + 9)
		self.transport.write( pack("!II5s%ds9s%ds" % (luser,ldb),
		l,                      # packet size 
        PG_PROTO_VERSION,       # protocol verison
		# username						  	
		"user\0", user,
		# database   
		"database\0", db,
		))

	# Authentication

	def auth_ok(self,data):
		self.auth = 1

	def auth_pass(self,data):
		"""Clear text authentication.
		"""
		pw = self.factory.password + "\0"
		lpw = len(pw)
		self.transport.write( pack("!sI%ss" % lpw,
		'p',
		lpw + 4,   # packet length
		pw,        # password
		))

	def auth_md5(self,data):
		"""MD5 pass auth.
		
		md5hex(md5hex(password + user) + <salt given by backend>)."""
		pw = "md5" + md5.new( md5.new(self.factory.password + self.factory.user).hexdigest() + data).hexdigest() + "\0"
		lpw = len(pw)
		self.transport.write( pack("!sI%ss" % lpw,
		'p',
		lpw + 4,   # packet length
		pw,        # password
		) )

	def packet_auth(self,data):
		'''Handle authentication requests.

		Switch on self.authMethods.
		'''
		(authtype,) = unpack("!I",data[:4])

		try:
			followup = self.authMethods[authtype]
		except:
#			raise NotSupportedError, ("Don't have a authenticator for auth type %s" % authtype)
			self.factory.conn._fail(NotSupportedError("Don't have a authenticator for auth type %s" % authtype))
			self.disconnect()
			self.factory.conn._pool.running -= 1
			return

		#print repr(data) # XXX
		followup(data[4:])
		self.switch()

	# Notice/Error
	def packet_notice(self,data):
		"""The backend wants to notice/warn us about something.
		"""
		parampairs = data.split("\0")[:-1]
		params = {}
		for item in parampairs:
			k,v = item[:1],item[1:]
			params[k] = v

		log.msg ("%s: %s" % (params["C"],params["M"]))

	def packet_error(self,data):
		"""The backend told us a fatal error has occurred.
		"""
		parampairs = data.split("\0")[:-1]
		params = {}
		for item in parampairs:
			k,v = item[:1],item[1:]
			params[k] = v

		#raise DatabaseError, ("[%s] %s: %s" % (params["S"],params["C"],params["M"]))
		if self.callbackQ:
			self.failure = DatabaseError("%s: %s" % (params["C"],params["M"]))
			cb = self.callbackQ.pop(0)
			if cb: cb()
			self.callbackQ = []
			self.queryQ = []
			self.inquery = 0
		else:
			self.factory.conn._fail(DatabaseError("%s: %s" % (params["C"],params["M"])))
			self.factory.conn._pool.running -= 1
			self.disconnect()

		self.switch()

	# Field Descriptions
	def packet_fields(self,data):
		"""This handles the information for each of the columns (fields) returned
		in the result set in response to a SELECT query.
		"""
		s = StringIO.StringIO(data)

		(numfields,) = unpack("!H",s.read(2))

		self.curfields = []
		pos = 2
		for field in range(numfields):
			ind = data.find("\0",pos)
			fieldname = s.read(ind - pos)
			pos = ind + 19 # leading null plus 18 of int
			( 
			null,
			tbloid,
			colattr,
			datatype,
			typesize,
			typemod,
			fmtcode,
			) = unpack("!sIHIHIH",s.read(19))
			self.curfields.append( (fieldname,datatype,typesize,typesize,None,None,None))

		self.switch()

	def packet_data(self,data):
		"""A row of data in response to a SELECT.  
		
		Handled by our Pyrex/C stuff because a lot of CPU time is spent here, and C does
		string scanning much better than python in that regard.
		"""
		self.datacache.add(data)
		self.switch()

	def packet_datadone(self,data):
		"""All rows have been sent."""
		self.switch()
		
	def packet_cmddone(self,data):
		"""A command has been successfully completed.

		Commands being (CREATE CURSOR-SELECT/UPDATE/INSERT/ROLLBACK/BEGIN/COMMIT/DELETE).
		"""
		#print "cmddone: " + data # XXX

		# Here's where we apply our type conversions from pgtypes 
		# to the appropriate data values. we cheat on int types and
		# use the builtin
		if data.startswith("FETCH"):
			if self.factory.unicode:
				oidMap = registry.getOIDMap('unicode')
			else:
				oidMap = registry.getOIDMap()
			try:
				self.rows = self.datacache.finish()
				cf = self.curfields
				for col in range(len(cf)):
					if cf[col][1] in oidMap:
						f = oidMap[cf[col][1]]
						for row in self.rows:
							if row[col] != None:
								row[col] = f(row[col])
			except DataError, m:
				self.failure = DataError(m)
				cb = self.callbackQ.pop(0)
				if cb: cb()
				return
				
		elif ( data.startswith("INSERT") or
  			   data.startswith("UPDATE") ):
			self.rowcount = int(data.split(" ")[-1][:-1])


		self.switch()

	def packet_cancel(self,data):
		"""This lets us know the cancellation key in case we need to cancel a command.

		This library doesn't support cancellation, but we hold onto the pid/key anyhow.
		"""
		self.pid, self.cancelKey = unpack("!II",data)
		self.switch()

	def packet_param(self,data):
		"""Set up a server-side param.

		We don't use this information, but we catalog it just in case.
		"""
		key,value,e = data.split("\0")
		self.params[key] = value
		self.switch()

	def packet_ready(self,data):
		"""Everything (including command done) has been sent related to the previous
		command or login.

		The server is now ready to handle another command.  This packet could be 
		considered the "idle state" of the backend.
		"""
		self.transStatus = PG_TRANS_MAP[data]
		if self.auth:
			self.auth = 0
			if self.factory.conn:
				self.factory.conn.factory = None
				self.factory.conn = None
			self.factory.pool.add(self.factory)

		# We're out of the query: callback
		elif self.inquery:
			self.inquery = 0

			cb = self.callbackQ.pop(0)
			if cb: cb()

			# do they want a release?
			while self.callbackQ and isinstance(self.callbackQ[0],ContinuingCallback):
				self.callbackQ.pop(0).func()
			
		self.switch()

		# Finally: execute next query in the queue
		if not self.inquery and self.queryQ:
			self._query(self.queryQ.pop(0))


	def packetSwitch(self,data):
		"""Do the first level of delegation after determining the packet type
		and packet length.
		"""
		op, l = unpack("!sI",data)
		#print "packet: %s" % op
		try:
			followup = self.packetMethods[op]
		except:
		#	raise NotSupportedError, ("No handler for server packet type %s" % op)
			self.failure = NotSupportedError("No handler for server packet type %s" % op)
			cb = self.callbackQ.pop(0)
			if cb: cb()
			return

		# no more bytes required?
		if l == 0:
			followup()
		else:
			self.terminatedDataReceived = followup
			self.terminator = l - 4


	# calls in:
	def callin_query(self,query,callback=None,now=0):
		"""The only call into the protocol layer.  
		
		'query' is a query/command.  callback is called when the command specified in 
		'query' is complete.  callback takes no args; the protocol doesn't keep 
		state for fe.py.

		now means insert this event in the front of the query queue: execute it ASAP
		"""
		if now:
			if self.inquery:
				# Index 1: leave the current query's callback!
				self.callbackQ.insert(1,callback) 
				self.queryQ.insert(0,query)
			else:
				self.callbackQ.insert(0,callback)
				self._query(query)
		else:
			self.callbackQ.append(callback)
			if self.inquery:
				self.queryQ.append(query)
			else:
				self._query(query)

	def _query(self,query):
		#print query # XXX
		self.inquery = 1
		self.curfields = []
		self.rows = []
		self.rowcount = -1
		query = query + "\0"
		ld = len(query)
		self.transport.write( pack("!sI%ds" % ld,
		'Q',    # query op
		ld + 4, # packet length
		query,      # query string
		))

	# disconnection
	def disconnect(self):
		"""Issue a disconnection packet and disconnect.
		"""
		self.transport.write( pack('!sI', 'X', 4))
		self.transport.loseConnection()
		self.factory.pg = None
		self.factory = None

class PgFactory(ClientFactory):
	"""A simple factory that manages PgProtocol.
	"""
	def __init__(self,pool,host,dbname,user,password,port=5432,unicode=False,conn=None):
		self.pool = pool
		self.dbname = dbname
		self.user = user
		self.password = password
		self.host = host
		self.port = port
		self.unicode = unicode
		self.conn = conn

		self.failure = None

	def buildProtocol(self,addr):
		self.pg = PgProtocol()
		self.pg.factory = self
		return self.pg

	def clientConnectionLost(self,connector,reason):
		if self.pg:
			self.pg.factory = None
			self.pg = None
		self.conn = None

	def clientConnectionFailed(self,connector,reason):
		self.conn._fail(OperationalError("Could not connect to database '%s' at %s:%s, %s" % 
		(self.dbname,self.host,self.port,reason)))
