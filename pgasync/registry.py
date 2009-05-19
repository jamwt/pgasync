'''Registry for type/oid conversion in and out of the database.'''

_registries = {}

class AdapterRegistrationError(Exception): pass

def copyRegistry(old, new):
	ro = _registries[old]
	_registries[new] = (ro[0].copy(), ro[1].copy(), ro[2][:])
	
def registerAdapter(adapter, types, oids, regkey='__default__'):
	r = _registries.get(regkey,None)
	if r is None:
		r = ({},{},[])
		_registries[regkey] = r

	typeMap, oidMap, adapters = r

	if hasattr(adapter, 'toDatabase'):
		a = adapter.toDatabase
	else:
		a = adapter

	for typ in types:
		typeMap[typ] = a

	if hasattr(adapter, 'fromDatabase'):
		a = adapter.fromDatabase
	else:
		a = adapter

	for oid in oids:
		oidMap[oid] = a

	adapters.append(adapter)

def typeToAdapter(typ, regkey='__default__'):
	return _registries[regkey][0].get(typ, None)

def getOIDMap(regkey='__default__'):
	return _registries[regkey][1]

def adapterInRegistry(adapter, regkey='__default__'):
	return adapter in _registries[regkey][2]

def isAdapterInstance(instance, regkey='__default__'):
	for adapter in _registries[regkey][2]:
		if isinstance(instance, adapter):
			return True
	return False
	
