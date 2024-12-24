#pragma once

#include <boost/asio.hpp>
#include <yaml-cpp/yaml.h>

namespace FluxCppCore {

    inline int32_t find_free_port() {
        boost::asio::io_service io;
        boost::asio::ip::tcp::acceptor acceptor(io, boost::asio::ip::tcp::endpoint(boost::asio::ip::tcp::v4(), 0));
        return static_cast<int32_t>(acceptor.local_endpoint().port());
    }

    int8_t inline get_market_depth_levels_from_config() {
        const char* config_file = getenv("CONFIG_FILE");
        // int8_t market_depth_levels;
        if (!config_file) {
            throw std::runtime_error("export env variable {CONFIG_FILE}");
        }
        if (access(config_file, F_OK) != 0) {
            throw std::runtime_error(std::format("{} not accessable", config_file));
        }
        YAML::Node config = YAML::LoadFile(config_file);
        return config["market_depth_levels"].as<int8_t>();
    }

    inline auto get_timespec_utc_as_str(const std::timespec &ts) {
        char buffer[32];
        auto n = std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%T", std::gmtime(&ts.tv_sec));
        return std::format("{}.{:0<6}{}", std::string_view(buffer, n), ts.tv_nsec/1000, "+00:00");
    }

    inline auto exch_time_to_timespec_utc(const unsigned long fht) {
        double d = 0.0;
        double fraction = std::modf(fht / 1000000000.0, &d);
        std::timespec ts{static_cast<long int>(d), static_cast<long>(fraction * 1'000'000'000)};
        return ts;
    }

    inline auto exch_time_to_str(const unsigned long fht) {
        return get_timespec_utc_as_str(exch_time_to_timespec_utc(fht));
    }

    inline auto time_in_utc_str(unsigned long fht) {
        double d = 0.0;
        double fraction = std::modf(fht / 1000.0, &d);
        std::timespec ts{static_cast<long int>(d), static_cast<long>(fraction * 1'000'000'000)};
        char buffer[32];
        auto n = std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%T", std::gmtime(&ts.tv_sec));
         return std::format("{}.{:0<3}", std::string_view(buffer, n), ts.tv_nsec/1000000);
    }

}