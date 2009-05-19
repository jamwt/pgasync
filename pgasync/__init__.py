from fe import *
from pgtypes import *
from util import *
from registry import *

# Postgres Object ID constants
class PgOids:
	BOOL      = 16 
	BYTEA     = 17 
	CHAR      = 18
	INT8      = 20 
	INT2      = 21 
	INT4      = 23 
	TEXT      = 25 
	FLOAT4    = 700 
	FLOAT8    = 701 
	ABSTIME   = 702 
	RELTIME   = 703 
	TINTERVAL = 704
	CASH      = 790 
	BPCHAR    = 1042 
	VARCHAR   = 1043 
	DATE      = 1082 
	TIME      = 1083 
	TIMESTAMP = 1114 
	INTERVAL  = 1186
	_NUMERIC  = 1231
	NUMERIC   = 1700
	CSTRING   = 2275 

import datetime
from decimal import Decimal

# Standard registry
registerAdapter(NULL, [type(None)],[])

registerAdapter(STRING, [str],[])
registerAdapter(BINARY, [unicode], [PgOids.BYTEA]) # No real unicode support in the default type registry

registerAdapter(NUMBER, [],[])
registerAdapter(int, [],[PgOids.INT2, PgOids.INT4])
registerAdapter(float, [],[PgOids.FLOAT4, PgOids.FLOAT8])
registerAdapter(long, [],[PgOids.INT8])
registerAdapter(Decimal, [],[PgOids.NUMERIC, PgOids._NUMERIC])
registerAdapter(ROWID, [], []) # 

registerAdapter(DATE, [datetime.date], [PgOids.DATE])
registerAdapter(TIME, [datetime.time], [PgOids.TIME,PgOids.ABSTIME,PgOids.RELTIME])
registerAdapter(DATETIME, [datetime.datetime], [PgOids.TIMESTAMP])

registerAdapter(BOOL, [bool], [PgOids.BOOL])

registerAdapter(MONEY, [], [PgOids.CASH])

# Unicode
copyRegistry('__default__','unicode')
registerAdapter(UNICODE, [unicode],[PgOids.BPCHAR, PgOids.CHAR, 
				PgOids.TEXT, PgOids.VARCHAR,],regkey='unicode')
