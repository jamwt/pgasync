"""Formatting of pyparams style args to execute.
"""
import datetime

# Sibling Imports
from pgtypes import *
from errors import *
from registry import *

from decimal import Decimal
# Types that are already suitable for str() representation
donetypes  = [STRING,UNICODE,BINARY,NUMBER,ROWID,DATETIME,BOOL,MONEY,int,float,Decimal]

def typeCastParam(p):
	"""Cast p to the appropriate type if possible.
	"""
	tp = type(p)

	# Already a valid adapter or type
	if adapterInRegistry(tp):
		return p

	cls = typeToAdapter(tp)

	if not cls:
		if isAdapterInstance(p):
			return p
		raise ProgrammingError, ("Query parameter: cannot convert %s to a PostgreSQL data type" % tp)
	
	return cls(p)

def format(s,params):
	"""Make params appear in s correctly.

	This includes pgsql specific date/time formats, safe strings, 
	binary sequences, etc
	"""

	s = s.strip()
	if s[-1] == ";":
		s = s[:-1]

	if params is None:
		return s

	if isinstance(params,tuple):
		tmp = tuple([typeCastParam(p) for p in params])
		params = tmp
	elif isinstance(params,dict):
		for k,v in params.items():
			params[k] = typeCastParam(v)
	else:
		params = typeCastParam(params)
	
	return s % params
