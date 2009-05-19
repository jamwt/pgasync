"""A set of types as required by the DB API 2.0.

All these types implement str() in a way that makes them correct and
safe for inclusion in commands passed to the backend.

This module uses datetime from the stdlib, which means we need Python 2.3+
"""

LOCALE_MONEY_DEFAULTS = ('$',',','.')

# System imports
import datetime
import string
import re

# Sibling imports
from errors import *

# Single quote isn't "printable" for us.. we need to muck with it
_printable = string.printable.replace("'","").replace("\\","")

class NULL:
	def __init__(self,v): pass

	def __str__(self):
		return "NULL"

_nchar_exp = re.compile(r'\\([0-9]{3}|\\)', re.MULTILINE)
class BINARY(str):
	def __str__(self):
		return "'" + "".join( [
		(char in _printable and 
		char or
		"\\\\%03o" % ord(char)) 
		for char in str.__str__(self)]) + "'"

	@staticmethod
	def fromDatabase(s):
		def replace(mo):
			try:
				return chr(int(mo.group(1),8))
			except:
				return '\\'
			
		return re.sub(_nchar_exp, replace, s)

class STRING(str): 
	def __str__(self):
		s = str.__str__(self)
		s = s.replace("\\","\\" + "134")
		return "'" + s.replace("'","''")  + "'"

class UNICODE(STRING):
	def __init__(self, v):
		STRING.__init__(v.encode('utf-8'))

	@staticmethod
	def fromDatabase(s):
		return STRING.fromDatabase(s).decode('utf-8')

class NUMBER: 
	def __init__(self,v):
		if type(v) in (int, float, Decimal):
			self.v = v		
			return

		raise DataError, ("Cannot convert '%s' to number (int,float)" % v)
	
	def __str__(self):
		return str(self.v)

	def __repr__(self):
		return repr(self.v)

	def __int__(self):
		return int(self.v)

	def __long__(self):
		return long(self.v)

	def __float__(self):
		return float(self.v)

	def __complex__(self):
		return complex(self.v)

class ROWID(NUMBER): pass

class DATE(datetime.date): 

	def __init__(self, *args):
		datetime.date.__init__(self, *args)

	@staticmethod
	def toDatabase(s):
		return "'%04d-%02d-%02d'" % (s.year,s.month,s.day)

	def __str__(self):
		return DATE.toDatabase(self)

	@staticmethod
	def fromDatabase(s):
		try:
			parts = map(int,s.split("-"))
			return datetime.date(*parts)
		except:
			raise DataError, ("Cannot convert string '%s' to datetime.date; only ISO-8601 output supported" % s)

class TIME(datetime.time): 
	def __init__(self, *args):
		datetime.time.__init__(self, *args)

	@staticmethod
	def toDatabase(s):
		return "'%02d:%02d:%02d.%06d'" % (s.hour, s.minute, s.second, s.microsecond)

	def __str__(self):
		return TIME.toDatabase(self)

	@staticmethod
	def fromDatabase(ins):
		if ins.count("-"):
			ins = ins.split("-")[0] #discarding timestamp for right tnow
				
		try:
			h,m,sparts = ins.split(":")
			h,m = map(int,(h,m))
			if sparts.count("."):
				ssegs = sparts.split(".")
				s,ms = map(int,ssegs)
				if ms:
					l = len(ssegs[1])
					ms *= 10 ** (6 - l)
			else:
				s = int(sparts)
				ms = 0
		except:
			raise DataError, ("Cannot convert string '%s' to datetime.time; only ISO-8601 output supported" % ins)
		return datetime.time(h,m,s,ms)

class DATETIME(datetime.datetime):
	def __init__(self,*args):
		datetime.datetime.__init__(self,*args)

	@staticmethod
	def toDatabase(s):
		return "'%s %s'" % (DATE.toDatabase(s)[1:-1], TIME.toDatabase(s)[1:-1])

	def __str__(self):
		return DATETIME.toDatabase(self)

	@staticmethod
	def fromDatabase(s):
		p1,p2 = s.split(" ")
		dt = DATE.fromDatabase(p1)
		tm = TIME.fromDatabase(p2)
		return datetime.datetime(dt.year,dt.month,dt.day,
		tm.hour,tm.minute,tm.second,tm.microsecond)

class BOOL:
	def __init__(self, b):
		self.__b = b
	def __str__(self):
		if self.__b:
			return "'T'"
		else:
			return "'F'"

	@staticmethod
	def fromDatabase(s):
		if s.upper().startswith("T"):
			return True
		if s.upper().startswith("F"):
			return False
		raise DataError, ("Cannot convert '%s' to boolean" % s)

from decimal import Decimal

import locale
_loc = locale.getdefaultlocale()[0]

if _loc:
	locale.setlocale(locale.LC_ALL, _loc)
	_thou_sep = locale.localeconv()['mon_thousands_sep']
	_cur_symbol = locale.localeconv()['currency_symbol']
	_dec_point = locale.localeconv()['mon_decimal_point']
else:
	_cur_symbol,  _thou_sep, _dec_point = LOCALE_MONEY_DEFAULTS

class MONEY:
	def __init__(self, v):
		if not type(v) == Decimal:
			raise DataError, ("Cannot convert '%s' to money; use Decimal" % type(v))
			
		self.v = v

	def __str__(self):
		return "'%s%s'" % (_cur_symbol, self.v)

	@staticmethod
	def fromDatabase(s):
		s = s.replace(_thou_sep, '').replace(_cur_symbol, '')
		if _dec_point != '.':
			s = s.replace(_dec_point, '.')
		return Decimal(s)
