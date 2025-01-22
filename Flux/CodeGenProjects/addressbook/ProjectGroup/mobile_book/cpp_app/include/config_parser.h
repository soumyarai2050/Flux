#pragma once

#include "cpp_app_logger.h"
#include "base_web_client.h"

#include "yaml-cpp/yaml.h"
#include "boost/core/demangle.hpp"

#include <optional>
#include <format>

#include "md_container.h"


enum class PublishPolicy {
    OFF,
    PRE,
    POST,
};


struct Config
{
    explicit Config(const std::string& config_file)
    {
        YAML::Node config = YAML::LoadFile(config_file);
        auto get_value_of = [&config, &config_file]<typename ValueT>(const char* param, bool required) -> std::optional<ValueT>
        {
            std::stringstream ss;
            ss << std::format("param: {}. converting to {}", param, boost::core::demangle(typeid(ValueT).name()));
            LOG_INFO_IMPL(GetCppAppLogger(), "{}", ss.str());

            try{
                if (!config[param].IsDefined())
                {
                    if (required)
                    {
                        std::stringstream sss;
                        sss << "Required field '" << param << "' is not defined in config file: " << config_file;
                        LOG_ERROR_IMPL(GetCppAppLogger(), "{}", sss.str());
                        throw std::runtime_error(sss.str());
                    } else {
                        return std::optional<ValueT>{};
                    }
                }
                auto val = config[param].as<ValueT>();
                return std::make_optional<ValueT>(val);
            }catch(std::exception& ex) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "{}", ex.what());
                std::runtime_error error(ex.what());
            }
        }; // lambda ends

        m_project_name_ = get_value_of.template operator()<std::string>(
            "project_name", false).value_or(std::string{});
        m_http_host_ = get_value_of.template operator()<std::string>(
            "http_ip", false).value_or(std::string{});
        m_http_port_ = get_value_of.template operator()<std::string>(
            "http_port", false).value_or(std::string{});
        m_mongodb_uri_ = get_value_of.template operator()<std::string>(
            "mongo_server", true).value_or(std::string{});
        m_db_name_ = get_value_of.template operator()<std::string>("db_name",
            true).value_or(std::string{});
        m_leg_1_symbol_ = get_value_of.template operator()<std::string>("leg_1_symbol",
            true).value_or(std::string{});
        m_leg_2_symbol_ = get_value_of.template operator()<std::string>("leg_2_symbol",
            true).value_or(std::string{});
        m_shm_cache_name_ = m_db_name_ + "_shm";
        m_shm_semaphore_name_ = m_db_name_ + "_sem";
        if (!getenv("LOG_DIR_PATH")) {
            throw std::runtime_error("LOG_DIR_PATH env is not set");
        }
        m_log_directory_ = getenv("LOG_DIR_PATH");
        m_binary_log_path_ = m_log_directory_ + "/bin_" + m_db_name_ + ".bin";
        m_swagger_ui_json_path_ = get_value_of.template operator()<std::string>("swagger_ui_json_path",
            true).value_or(std::string{});

        m_ws_port_ = get_value_of.template operator()<int32_t>("cpp_ws_port",
            false).value_or(0);
        m_http_server_port_ = get_value_of.template operator()<int32_t>("cpp_http_port", true).value_or(0);
        m_market_depth_level_ = get_value_of.template operator()<size_t>("market_depth_level", true).value_or(0);

        m_market_depth_db_update_publish_policy_ = static_cast<PublishPolicy>(get_value_of.template operator()<int32_t>(
            "market_depth_db_update_publish_policy", false).value_or(0));
        m_top_of_book_db_update_publish_policy_ = static_cast<PublishPolicy>(get_value_of.template operator()<int32_t>(
            "top_of_book_db_update_publish_policy", false).value_or(0));
        m_last_barter_db_update_publish_policy_ = static_cast<PublishPolicy>(get_value_of.template operator()<int32_t>(
            "last_barter_db_update_publish_policy", false).value_or(0));

        m_market_depth_http_update_publish_policy_ = static_cast<PublishPolicy>(get_value_of.template operator()<int32_t>(
            "market_depth_http_update_publish_policy", false).value_or(0));
        m_top_of_book_http_update_publish_policy_ = static_cast<PublishPolicy>(get_value_of.template operator()<int32_t>(
            "top_of_book_http_update_publish_policy", false).value_or(0));
        m_last_barter_http_update_publish_policy_ = static_cast<PublishPolicy>(get_value_of.template operator()<int32_t>(
            "last_barter_http_update_publish_policy", false).value_or(0));

        m_market_depth_ws_update_publish_policy_ = static_cast<PublishPolicy>(get_value_of.template operator()<int32_t>(
            "market_depth_ws_update_publish_policy", false).value_or(0));
        m_top_of_book_ws_update_publish_policy_ = static_cast<PublishPolicy>(get_value_of.template operator()<int32_t>(
            "top_of_book_ws_update_publish_policy", false).value_or(0));
        m_last_barter_ws_update_publish_policy_ = static_cast<PublishPolicy>(get_value_of.template operator()<int32_t>(
            "last_barter_ws_update_publish_policy", false).value_or(0));

        m_shm_update_publish_policy_ = static_cast<PublishPolicy>(get_value_of.template operator()<int32_t>(
            "cpp_shm_update_publish_policy", false).value_or(0));

        m_md_client_config_ = {
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + create_market_depth_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + get_market_depth_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + get_market_depth_max_id_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + put_market_depth_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + patch_market_depth_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + delete_market_depth_client_url
        };
        m_tob_client_config_ = {
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + create_top_of_book_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + get_top_of_book_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + get_top_of_book_max_id_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + put_top_of_book_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + patch_top_of_book_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + delete_top_of_book_client_url
        };

        m_lt_client_config_ = {
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + create_last_barter_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + get_last_barter_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + get_last_barter_max_id_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + put_last_barter_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + patch_last_barter_client_url,
            PATH_SEPARATOR + m_project_name_ + PATH_SEPARATOR + delete_last_barter_client_url
        };

    }

    std::string m_project_name_;
    std::string m_http_host_;
    std::string m_http_port_;
    std::string m_mongodb_uri_;
    std::string m_db_name_;
    std::string m_leg_1_symbol_;
    std::string m_leg_2_symbol_;
    std::string  m_shm_cache_name_;
    std::string m_shm_semaphore_name_;
    std::string m_log_directory_;
    std::string m_binary_log_path_;
    std::string m_raw_log_path_;
    std::string m_swagger_ui_json_path_;
    std::string m_top_of_book_ws_route_{"/get-all-top_of_book-ws"};
    std::string m_market_depth_ws_route_{"/get-all-market_depth-ws"};
    std::string m_last_barter_ws_route_{"/get-all-last_barter-ws"};

    int32_t m_ws_port_;
    int32_t m_http_server_port_;
    size_t m_market_depth_level_;

    PublishPolicy m_market_depth_db_update_publish_policy_;
    PublishPolicy m_top_of_book_db_update_publish_policy_;
    PublishPolicy m_last_barter_db_update_publish_policy_;
    PublishPolicy m_market_depth_http_update_publish_policy_;
    PublishPolicy m_top_of_book_http_update_publish_policy_;
    PublishPolicy m_last_barter_http_update_publish_policy_;
    PublishPolicy m_market_depth_ws_update_publish_policy_;
    PublishPolicy m_top_of_book_ws_update_publish_policy_;
    PublishPolicy m_last_barter_ws_update_publish_policy_;
    PublishPolicy m_shm_update_publish_policy_;

    FluxCppCore::ClientConfig m_md_client_config_;
    FluxCppCore::ClientConfig m_tob_client_config_;
    FluxCppCore::ClientConfig m_lt_client_config_;

};
