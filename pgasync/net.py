# System imports
try:
	import cStringIO as StringIO
except ImportError:
	import StringIO

# Twisted imports
from twisted.internet.protocol import Protocol

class CountTerminatedProtocol(Protocol):
	"""A Protocol which terminates on a certian # of bytes read.  

	It handles buffering by way of cStringIO.
	"""
	def __init__(self, terminator=0):
		self.terminator = terminator

		self.__inbuf = StringIO.StringIO()
		self._bread = 0

	def dataReceived(self,buf):
		"""Buffer it until we have self.terminator bytes.
		"""
		self._bread += len(buf)
		self.__inbuf.write(buf)

		if self._bread >= self.terminator:
			self.__inbuf.seek(0)
			while self.terminator and self.terminator <= self._bread:
				x = self.__inbuf.read(self.terminator)
				t = self.terminator
				self.terminatedDataReceived(x)
				self._bread -= t
			
			t = self.__inbuf.read()
			self.__inbuf.seek(0)
			self.__inbuf.truncate()
			self.__inbuf.write(t)

	#############################
	# User-defined functions
	def terminatedDataReceived(self,data):
		"""terminatedDataReceived
		----------------------
		terminatedDataReceived is called when there is data read from the socket that 
		meets the termination criteria 

		 * First argument is the input data
		"""
		pass
