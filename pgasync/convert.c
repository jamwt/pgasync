/* provide some nice conversion functions 
 * for cache.pyx to use to reverse the network
 * byte order.
 * */
#include "convert.h"

inline unsigned short convertUShort(char *s){
	unsigned short *p = (unsigned short *)s;
	return ntohs(*p);
}

inline int convertInt(char *s){
	unsigned int *p = (unsigned int *)s;
	return (int)ntohl(*p);
}
