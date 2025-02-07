#pragma once

#include <chrono>
#include <sstream>
#include <ctime>
#include <cstring>

#include <bsoncxx/types.hpp>
#include <date/date.h>
#include "market_data_constants.h"

namespace FluxCppCore {

    template<typename T>
    T get_local_time_microseconds();

    template<>
    inline std::string get_local_time_microseconds<std::string>() {
        // Get the current time
        auto now = std::chrono::system_clock::now();

        std::time_t now_time_t = std::chrono::system_clock::to_time_t(now);
        std::tm tm = *std::localtime(&now_time_t);
        auto duration = now.time_since_epoch();
        auto microseconds = std::chrono::duration_cast<std::chrono::microseconds>(duration).count() % 1000000;
        std::ostringstream ss;
        ss << std::put_time(&tm, "%Y-%m-%dT%H:%M:%S")
        << '.' << std::setfill('0') << std::setw(6) << microseconds // Print microseconds (6 digits)
        << "+00:00";
        return ss.str();
    }

    template<>
    inline int64_t get_local_time_microseconds<int64_t>() {
        // Get the current system time
        auto now = std::chrono::system_clock::now();
        auto duration = now.time_since_epoch();
        return std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
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
            std::istringstream ss{utc_time_str};
            std::chrono::system_clock::time_point tp;
            ss >> date::parse("%FT%T%z", tp);
            // bsoncxx::types::b_decimal128
            return bsoncxx::types::b_date{tp};
        }

        static inline bsoncxx::types::b_date convert_utc_string_to_b_date(const int64_t& timestamp_ms) {
            return bsoncxx::types::b_date{std::chrono::milliseconds(timestamp_ms)};
        }
#if 0
        static void inline setString(char* dest, const char* src, const size_t size) {
            strncpy(dest, src, size - 1);
            dest[size - 1] = '\0';
        }
#endif

        template <size_t DestSize, typename SourceType>
        static void inline setString(char (&dest)[DestSize], const SourceType& src) {
            static_assert(DestSize == market_data_handler::MAX_STRING_LENGTH);
            static_assert(std::is_same_v<SourceType, std::string> || std::is_same_v<SourceType, std::string_view>);
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wstringop-truncation"
            std::strncpy(dest, src.data(), src.size());
#pragma GCC diagnostic pop
            dest[src.size()] = '\0';
         }

        template <size_t DestSize>
        static void inline setString(char (&dest)[DestSize], const char (&src)[DestSize]) {
            static_assert(DestSize == market_data_handler::MAX_STRING_LENGTH);
            // static_assert(std::is_same_v<SourceType, std::string> || std::is_same_v<SourceType, std::string_view>);
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wstringop-truncation"
            std::strncpy(dest, src, DestSize);
#pragma GCC diagnostic pop
            dest[DestSize] = '\0';
         }
    };
}
