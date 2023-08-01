#ifndef FLUX_TIMESUPPORT
#define FLUX_TIMESUPPORT
 
#ifdef _WIN32
 
#define SNPRINTF _snprintf
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <time.h>
#include <iostream>
#include <tchar.h>
#if defined(_MSC_VER) || defined(__BORLANDC__)
#define EPOCHFILETIME (116444736000000000i64)
#else
#define EPOCHFILETIME (116444736000000000LL)
#endif
 
struct timezone {
       int tz_minuteswest; /* minutes W of Greenwich */
       int tz_dsttime;     /* type of dst correction */
};
 
 
 
#else  /* _WIN32 */
#define SNPRINTF snprintf
#include <sys/time.h>
#include <stdio.h>
 
#endif /* _WIN32 */
 
       inline bool operator!=(timeval tv1, timeval tv2)
       {
              return (tv1.tv_sec!=tv2.tv_sec || tv1.tv_usec!=tv2.tv_usec);
       }
 
       inline bool operator==(timeval tv1, timeval tv2)
       {
              return (tv1.tv_sec==tv2.tv_sec && tv1.tv_usec==tv2.tv_usec);
       }
 
 
 
class Time
{
public:
 
       static timeval GetUtcDateTime()
       {
              struct timeval tv;
              struct timezone tz;
              GetTimeOfDay(&tv,&tz);
              //tv.tv_sec += (tz.tz_minuteswest*60);//ANDREW
              return tv;
       }
 
       static int GetTimeOfDay(struct timeval *tv, struct timezone *tz)
       {
#ifdef WIN32
              FILETIME        ft;
              LARGE_INTEGER   li;
              __int64         t;
              static int      tzflag;
 
              if (tv)
              {
                     GetSystemTimeAsFileTime(&ft);
              
                     
                     li.LowPart  = ft.dwLowDateTime;
                     li.HighPart = ft.dwHighDateTime;
                     t  = li.QuadPart;       /* In 100-nanosecond intervals */
                     t -= EPOCHFILETIME;     /* Offset to the Epoch time */
                     t /= 10;                /* In microseconds */
                     tv->tv_sec  = (long)(t / 1000000);
                     tv->tv_usec = (long)(t % 1000000);
              }
 
              if (tz)
              {
                     if (!tzflag)
                     {
                           _tzset();
                           tzflag++;
                     }
                     tz->tz_minuteswest = _timezone / 60;
                     tz->tz_dsttime = _daylight;
              }
              
              return 0;
#else // WIN32
              return gettimeofday(tv,tz);
#endif
       }
 
       static time_t GetTimeFromTimeVal( timeval tv )
       {
              return tv.tv_sec;
       }
 
       static int GetMilliseconds( timeval tv )
       {
              return (int)(tv.tv_usec/1000);
       }
 
       static timeval GetTimeFromString( const char *buffer, int length )
       {
              struct tm tm = {0,0,0,0,0,0};
              int milliseconds;
        bool isDayError = true;
              sscanf(buffer,"%d-%d-%dT%d:%d:%d.%d",&tm.tm_year, &tm.tm_mon, &tm.tm_mday, &tm.tm_hour, &tm.tm_min, &tm.tm_sec, &milliseconds);
              tm.tm_year -= 1900;
              tm.tm_mon --;
              time_t t = GetTimeFromStructTm(&tm);
              timeval tv;
              tv.tv_sec = (long)t;
              tv.tv_usec = milliseconds * 1000;
              return tv;
       }
 
       // convert a local time
       static int GetStringFromTime( timeval tv, char *buffer, int length )
       {
              time_t t = (time_t)(tv.tv_sec);
              struct tm gmTime;
              UtcTimeToStructTm(t, &gmTime);  // OS independent call use local function 
              int milliseconds = Time::GetMilliseconds(tv);
              gmTime.tm_year += 1900;
              gmTime.tm_mon ++;
              return SNPRINTF(buffer,length,"%04d-%02d-%02dT%02d:%02d:%02d.%03d", gmTime.tm_year, gmTime.tm_mon, gmTime.tm_mday, gmTime.tm_hour, gmTime.tm_min, gmTime.tm_sec,milliseconds);
       }
 
       static timeval GetDefaultTime()
       {
              timeval tv = {0,0};
              return tv;
       }
              
       static time_t GetTimeFromStructTm( struct tm *tm )
       {
#ifdef WIN32
              return _mkgmtime(tm);
#elif defined __sun
              // the implementation is taken from http://csourcesearch.net/package/gpsd/2.25/gpsd-2.25/gpsutils.c/function/mkgmtime/20,1
              unsigned short year;
              time_t result;
              static const int cumdays[12] = {0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334};
              year = 1900 + tm->tm_year + tm->tm_mon / 12;
              result = (year - 1970) * 365 + cumdays[tm->tm_mon % 12];
              result += (year - 1968) / 4;
              result -= (year - 1900) / 100;
              result += (year - 1600) / 400;
              result += tm->tm_mday - 1;
              result *= 24;
              result += tm->tm_hour;
              result *= 60;
              result += tm->tm_min;
              result *= 60;
              result += tm->tm_sec;
        if( !(tm->tm_year % 4) && (0 == tm->tm_mon || 1 == tm->tm_mon))
        {
            result -= (24*60*60);
        }
              return result;
#else
        return timegm(tm);
#endif
       }
 
       // Converts a time_t (seconds since epoch) to a struct tm for individual components
       static void UtcTimeToStructTm( time_t t, struct tm *tm)
       {
#ifdef WIN32
              gmtime_s(tm,&t);
#else
              *tm = *gmtime(&t);   // don't copy pointer
#endif
       }
 
 
};
#endif //FLUX_TIMESUPPORT

