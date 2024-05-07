#pragma once

#include <bsoncxx/types.hpp>
#include <chrono>
#include <sstream>
#include <ctime>

namespace FluxCppCore {

    enum class TimeComparison {
        TIME1_LATER,
        TIME2_LATER,
        BOTH_EQUAL
    };


    class StringUtil {
    public:
        std::string str_tolower(std::string messgage_name)
        {
            std::transform(messgage_name.begin(), messgage_name.end(), messgage_name.begin(), [](unsigned char c){ return std::tolower(c); });
            return messgage_name;
        }

        std::string camel_to_snake(std::string msg_name)
        {

            // Empty String
            std::string result = "";

            // Append first character(in lower case)
            // to result string
            char c = std::tolower(msg_name[0]);
            result+=(char(c));

            // Traverse the string from
            // ist index to last index
            for (int i = 1; i < msg_name.length(); i++) {

                char ch = msg_name[i];

                // Check if the character is upper case
                // then append '_' and such character
                // (in lower case) to result string
                if (std::isupper(ch)) {
                    result = result + '_';
                    result+=char(std::tolower(ch));
                }

                    // If the character is lower case then
                    // add such character into result string
                else {
                    result = result + ch;
                }
            }

            // return the result
            return result;
        }

        static bsoncxx::types::b_date convert_utc_string_to_b_date(const std::string& utc_time_str) {
            std::tm tm = {};
            std::istringstream ss(utc_time_str);
            ss >> std::get_time(&tm, "%Y-%m-%d %H:%M:%S"); // Parse the date-time part

            // Parse microseconds
            char ch;
            ss >> ch; // skip the '.'
            int microseconds = 0;
            if (ss >> microseconds) {
                while (microseconds >= 1000000) // ensure microseconds are in correct range
                    microseconds /= 10;
            }

            // Parse timezone
            ss >> ch; // skip the '+'
            int timezone = 0;
            if (ss >> timezone) {
                tm.tm_hour -= timezone / 100; // adjust the hour
                tm.tm_min -= timezone % 100; // adjust the minute
            }

            std::time_t tt = timegm(&tm);
            std::chrono::system_clock::time_point tp = std::chrono::system_clock::from_time_t(tt);
            auto duration_since_epoch = std::chrono::duration_cast<std::chrono::milliseconds>(tp.time_since_epoch());

            // Add microseconds to the duration
            duration_since_epoch += std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::microseconds(microseconds));

            return bsoncxx::types::b_date(duration_since_epoch);
        }



        static TimeComparison find_latest_time(const std::string& time1_str, const std::string& time2_str) {
            if (time1_str > time2_str) {
                return TimeComparison::TIME1_LATER;
            } else if (time2_str > time1_str) {
                std::cout << time2_str << std::endl;
                return TimeComparison::TIME2_LATER;
            } else {
                // std::cout << "time1_str: " << time1_str << " time2_str: " << time2_str << std::endl;
                return TimeComparison::BOTH_EQUAL;
            }
        }


    };
}