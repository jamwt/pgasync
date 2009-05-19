from pgtypes import *

def Date(y,m,d): 
	dt = DATETIME(y,m,d)
	dt._tm = 0
	return dt

def Time(h,m,s,ms=0): 
	dt = DATETIME(1,1,1,h,m,s,ms)
	dt._dt = 0
	return dt

def Timestamp(y,mo,d,h,m,s,ms=0): return DATETIME(y,mo,d,h,m,s,ms)

def DateFromTicks(t):
	dt = DATETIME.fromtimestamp(t)
	dt._tm = 0
	return dt

def TimeFromTicks(t):
	dt = DATETIME.fromtimestamp(t)
	dt._dt = 0
	return dt

def TimestampFromTicks(t): return DATETIME.fromtimestamp(t)

def Binary(s): return BINARY(s)
