#ifndef SPARROW_WINDOWS_COMPAT_H
#define SPARROW_WINDOWS_COMPAT_H
/* Minimal Windows equivalents for the POSIX calls used by upstream Sparrow.
   User CPU time drives its reported statistics. User+kernel time drives the
   --timeout limit, checked in the search loop every 16384 flips. */
#include <windows.h>

struct tms {
    long tms_utime;
    long tms_stime;
    long tms_cutime;
    long tms_cstime;
};

static unsigned long long sparrow_filetime_ticks(FILETIME t) {
    ULARGE_INTEGER v;
    v.LowPart = t.dwLowDateTime;
    v.HighPart = t.dwHighDateTime;
    return v.QuadPart;
}

static double sparrow_process_cpu_seconds(void) {
    FILETIME created, exited, kernel, user;
    if (!GetProcessTimes(GetCurrentProcess(), &created, &exited, &kernel, &user)) {
        return 0.0;
    }
    return (double)(sparrow_filetime_ticks(user) + sparrow_filetime_ticks(kernel)) / 10000000.0;
}

static long sparrow_times(struct tms *t) {
    FILETIME created, exited, kernel, user;
    if (!GetProcessTimes(GetCurrentProcess(), &created, &exited, &kernel, &user)) {
        return -1;
    }
    t->tms_utime = (long)(sparrow_filetime_ticks(user) / 10000ULL);
    t->tms_stime = (long)(sparrow_filetime_ticks(kernel) / 10000ULL);
    t->tms_cutime = 0;
    t->tms_cstime = 0;
    return (long)GetTickCount();
}

#undef _SC_CLK_TCK
#define _SC_CLK_TCK 1
#define sysconf(name) (1000L)
#define times(t) sparrow_times(t)
#endif
