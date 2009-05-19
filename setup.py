REBUILD_PYREX = False

import sys

if REBUILD_PYREX:
	try:
		from Pyrex.Distutils import build_ext
	except ImportError:
		raise ImportError, "You specified REBUILD_PYREX, but Pyrex doesn't seem to be installed"
	else:
		CACHE = 'pgasync/cache.pyx'
		kwargs = {'cmdclass': {'build_ext': build_ext}}
else:
	CACHE = 'pgasync/cache.c'
	kwargs = {}

from distutils.core import setup
from distutils.extension import Extension


setup(
	name = "pgasync",
	version="2.01",
	author="Jamie Turner",
	author_email="jamwt@jamwt.com",
	url="http://jamwt.com/pgasync/",
	description="A twisted-based asyncronous DB API 2.0-conforming PostgreSQL client library",
	packages=["pgasync"],
	ext_modules = [
		Extension("pgasync.cache", [CACHE, "pgasync/convert.c"],),
    ],
    **kwargs
)
