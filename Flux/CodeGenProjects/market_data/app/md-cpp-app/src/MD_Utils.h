
#pragma once

#include <cmath>
#include <limits>
#include <ctime>
#include <string>
#include <chrono>

namespace md_handler{

    template<typename T>
    inline void setMillisecondsSinceEpochNow(T &obj){
        std::chrono::milliseconds ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch());
        const bsoncxx::types::b_date current_date_time(ms);
        obj.setMillisecondsSinceEpoch(current_date_time.to_int64());
    }

    inline std::string get_date_time_str_from_milliseconds(int64_t time_in_milliseconds){
        // handle not set
        if (0 == time_in_milliseconds) return "";

        //zoned_time{current_zone(), p1}
        char buf[sizeof "2011-10-08T07:07:09XXXZ--------"];
        std::time_t objTime_t(static_cast<int64_t>(time_in_milliseconds / 1000));
        time(&objTime_t);
        struct tm tm_{};
        strftime(buf, sizeof buf, "%FT%TZ", gmtime_r(&objTime_t, &tm_));
        //auto tm_date = std::localtime(&objTime_t);
        //strftime(buf, sizeof(buf), "%m/%d/%Y %H:%M:%S", tm_date);
        return {buf};
    }

    inline std::chrono::milliseconds get_chrono_ms_from_int64(int64_t time_in_milliseconds){
        std::chrono::duration<int64_t, std::milli> duration(time_in_milliseconds);
        std::chrono::milliseconds ms(duration);
        return ms;
    }

    // Not used - might need this later
    // Parses only YYYY-MM-DDTHH:MM:SSZ
    inline time_t parseiso8601utc(const char *date) {
        struct tm tt = {0};
        double seconds;
        if (sscanf(date, "%04d-%02d-%02dT%02d:%02d:%lfZ",
                   &tt.tm_year, &tt.tm_mon, &tt.tm_mday,
                   &tt.tm_hour, &tt.tm_min, &seconds) != 6)
            return -1;
        tt.tm_sec   = (int) seconds;
        tt.tm_mon  -= 1;
        tt.tm_year -= 1900;
        tt.tm_isdst =-1;
        return mktime(&tt) - timezone;
    }

    inline void time_t_conversion_samples()
    {
        time_t t = time(nullptr);
        std::cout << "UTC: " << asctime(gmtime(&t)) << std::endl;
        std::cout << "local: " << asctime(localtime(&t)) << std::endl;
        // POSIX-specific
        char timeZone[]{"TZ=Asia/Singapore"};
        putenv(timeZone);
        std::cout << "Singapore: " << asctime(localtime(&t)) << std::endl;

        struct tm buf{};
        char str[26];
        asctime_r(gmtime_r(&t, &buf), str);
        std::cout << "UTC: " << str << std::endl;
        asctime_r(localtime_r(&t, &buf), str);
        std::cout << "local: " << str << std::endl;
    }
}

