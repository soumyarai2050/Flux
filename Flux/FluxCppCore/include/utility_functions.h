#pragma once

#include <boost/asio.hpp>
#include <yaml-cpp/yaml.h>

#include "market_data_service.pb.h"
#include "string_util.h"

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

}