#ifndef CONVERT_H
#define CONVERT_H

#ifdef __linux__
#include <netinet/in.h>
#endif /* __linux__ */

#ifdef __FreeBSD__
#include <sys/param.h>
#endif /* __FreeBSD__ */

// netbsd/openbsd #include <sys/types.h>

inline unsigned short convertUShort(char *s);
inline int convertInt(char *s);

#endif /* CONVERT_H */
