#pragma once

#include <bsoncxx/types.hpp>
#include <chrono>
#include <sstream>
#include <ctime>

namespace FluxCppCore {

    inline int64_t get_utc_time_microseconds() {
        // Get the current time
        auto now = std::chrono::system_clock::now();
        // Get the current time as microseconds since the epoch
        auto now_as_us = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch());
        return static_cast<int64_t>(now_as_us.count());
    }

    inline std::string format_time(int64_t timestamp_ms) {
        // Convert milliseconds to microseconds
        auto timestamp_us = std::chrono::microseconds(timestamp_ms * 1000);
        // Convert the provided timestamp to system_clock time_point
        auto now = std::chrono::system_clock::time_point(timestamp_us);
        // Convert to time_t for use with gmtime
        auto now_as_time_t = std::chrono::system_clock::to_time_t(now);
        // Convert to tm for use with put_time
        std::tm* now_as_tm = std::localtime(&now_as_time_t);
        // Get the current time as microseconds since the epoch
        auto now_as_us = std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch());
        // The number of microseconds that have passed since the last second
        auto us = now_as_us.count() % 1000000;
        // Create a stream and output the formatted time
        std::ostringstream oss;
        oss << std::put_time(now_as_tm, "%Y-%m-%d %H:%M:%S") << '.' << std::setfill('0') << std::setw(6) << us << "+00:00";
        return oss.str();
    }

    inline int64_t parse_time(const std::string& time_str) {
        // Create a stringstream to parse the string
        std::istringstream iss(time_str);
        // Create tm struct to store parsed time
        std::tm tm = {};
        // Parse the string into tm struct
        iss >> std::get_time(&tm, "%Y-%m-%d %H:%M:%S");
        // Check if parsing succeeded
        if (iss.fail()) {
            throw std::runtime_error("Failed to parse time string");
        }
        // Convert tm to time_t
        auto time_t = std::mktime(&tm);
        // Convert time_t to microseconds since epoch
        auto timestamp_us = std::chrono::system_clock::from_time_t(time_t);

        // Extract microseconds from the time string
        char dot;
        int microseconds;
        if (iss >> dot >> microseconds) {
            // Add microseconds to timestamp
            timestamp_us += std::chrono::microseconds(microseconds);
        }

        // Return timestamp in microseconds
        return std::chrono::duration_cast<std::chrono::microseconds>(timestamp_us.time_since_epoch()).count() / 1000;
    }

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
            for (size_t i = 1; i < msg_name.length(); i++) {

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

    };
}