"""A fast implementation to read in data rows.
"""

cdef extern from "convert.h":
	unsigned short convertUShort(char *s)
	int convertInt(char *s)

cdef extern from "stdlib.h":
	void * malloc(int i)
	void free(void * buf)

cdef extern from "string.h":
	char * strncpy(char *dst, char *src,int l)

cdef class Cache:
	"""A Cache class for data rows.
	"""

	cdef char *buffer
	cdef int blen
	cdef list 

	def __new__(self):
		self.buffer = NULL
		self.blen = 0
		self.list = []

	def realloc(self):
		if self.blen == 0:
			self.blen = 1024
		else:
			self.blen = self.blen * 2
			free(self.buffer)
		self.buffer = <char *>malloc(self.blen)

	def add(self,ps):
		"""Adds a new row to the table.
		"""
		cdef unsigned short int ncol
		cdef int fsiz
		cdef char *s
		cdef int bitset

		s = ps

		row = []
		ncol = convertUShort(s)

		s = &s[2]

		for i from 0 <= i < ncol:
			fsiz = convertInt(s)

			s = &s[4]

			if fsiz <= 0:
				row.append(None)
				continue

			while fsiz + 1 > self.blen:
				self.realloc()

			strncpy(self.buffer,s,fsiz)
			self.buffer[fsiz] = 0
			row.append(self.buffer)
			s = &s[fsiz]

		self.list.append(row)

	def finish(self):
		free(self.buffer)
		self.buffer = NULL
		self.blen = 0
		l = self.list
		self.list = []
		return l
