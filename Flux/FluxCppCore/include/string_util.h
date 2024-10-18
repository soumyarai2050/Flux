#pragma once

#include <bsoncxx/types.hpp>
#include <chrono>
#include <sstream>
#include <ctime>

namespace FluxCppCore {

    inline std::string get_utc_time_microseconds() {
        // Get the current time
        auto now = std::chrono::system_clock::now();

        // Get the current time as milliseconds since the epoch
        auto now_as_ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch());
        auto timestamp_ms = static_cast<int64_t>(now_as_ms.count());

        // Convert milliseconds to microseconds
        auto timestamp_us = std::chrono::microseconds(timestamp_ms * 1000);

        // Convert to system_clock time_point
        auto time_point = std::chrono::system_clock::time_point(timestamp_us);

        // Convert to time_t for use with localtime
        auto time_t_value = std::chrono::system_clock::to_time_t(time_point);

        // Convert to tm for formatting
        std::tm* now_as_tm = std::localtime(&time_t_value);

        // Get the current time as microseconds since the epoch
        auto now_as_us = std::chrono::duration_cast<std::chrono::microseconds>(time_point.time_since_epoch());

        // The number of microseconds that have passed since the last second
        auto us = now_as_us.count() % 1000000;

        // Create a stream and output the formatted time
        std::ostringstream oss;
        oss << std::put_time(now_as_tm, "%Y-%m-%d %H:%M:%S")
            << '.' << std::setfill('0') << std::setw(6) << us
            << "+00:00";

        return oss.str();
    }

    inline int64_t parse_time(const std::string& time_str) {
        std::istringstream iss(time_str);
        std::tm tm = {};
        char separator;

        // Check the separator between date and time
        if (time_str.find('T') != std::string::npos) {
            separator = 'T';
        } else if (time_str.find(' ') != std::string::npos) {
            separator = ' ';
        } else {
            throw std::runtime_error("Invalid time string format");
        }

        // Parse the string into tm struct
        iss >> std::get_time(&tm, ("%Y-%m-%d" + std::string(1, separator) + "%H:%M:%S").c_str());

        // Check if parsing succeeded
        if (iss.fail()) {
            throw std::runtime_error("Failed to parse time string");
        }

        // Check for fractional seconds
        int64_t microseconds = 0;
        if (iss.peek() == '.') {
            iss.get(); // consume the '.'
            std::string fractional_seconds;
            std::getline(iss, fractional_seconds);
            // Convert fractional seconds to microseconds
            microseconds = std::stoll(fractional_seconds);
            // Ensure we only take the first 6 digits for microseconds
            if (microseconds >= 1000000) {
                throw std::runtime_error("Fractional seconds exceed 6 digits");
            }
        }

        // Convert tm to time_t
        time_t time_t_value = std::mktime(&tm);
        if (time_t_value == -1) {
            throw std::runtime_error("Failed to convert tm to time_t");
        }

        // Convert time_t to milliseconds since epoch
        auto timestamp_ms = std::chrono::system_clock::from_time_t(time_t_value);
        auto total_ms = std::chrono::duration_cast<std::chrono::milliseconds>(timestamp_ms.time_since_epoch()).count();

        // Convert microseconds to milliseconds (by dividing by 1000) and add
        return total_ms + microseconds / 1000;
    }


    inline void format_time(int64_t timestamp_ms, std::string &time_str_out) {
        // Convert time_t to time_point
        std::chrono::system_clock::time_point tp = std::chrono::system_clock::from_time_t(timestamp_ms);

        // Convert to std::tm
        std::time_t tt = std::chrono::system_clock::to_time_t(tp);
        std::tm tm = *std::localtime(&tt); // Use gmtime to get UTC time

        // Get the milliseconds
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                      tp.time_since_epoch()) % 1000;

        // Format the string
        std::ostringstream oss;
        oss << std::put_time(
                   &tm, "%Y-%m-%d %H:%M:%S") << "." << std::setfill('0') << std::setw(
                                               3) << ms.count() << "+00:00";

        time_str_out =  oss.str();
    }

    class StringUtil {
    public:
        static std::string str_tolower(std::string messgage_name)
        {
            std::transform(messgage_name.begin(), messgage_name.end(), messgage_name.begin(), [](unsigned char c){ return std::tolower(c); });
            return messgage_name;
        }

        static std::string camel_to_snake(std::string msg_name)
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
                    result.append("_");
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

        static inline bsoncxx::types::b_date convert_utc_string_to_b_date(const std::string& utc_time_str) {
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