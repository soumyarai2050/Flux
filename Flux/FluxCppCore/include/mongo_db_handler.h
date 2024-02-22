#pragma once

#include <unordered_map>

#include <bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/json.hpp>
#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>
#include <mongocxx/pool.hpp>

#include "../../generated/CppUtilGen/market_data_constants.h"
#include "quill/Quill.h"

namespace FluxCppCore {

    using bsoncxx::builder::basic::make_array;
    using bsoncxx::builder::basic::make_document;
    using bsoncxx::builder::basic::kvp;

    inline void get_symbol_side_query(const std::string &symbol, const std::string &side, bsoncxx::builder::stream::document &query_out){
        query_out << market_data_handler::symbol_fld_name << symbol << market_data_handler::side_fld_name << side
                  << bsoncxx::builder::stream::finalize;
    }

    class MongoDBHandler {
    public:
        explicit MongoDBHandler(quill::Logger* p_logger = quill::get_logger(), const int min_pool_size = 1, const int max_pool_size = 1):
        str_uri(market_data_handler::db_uri + "/?minPoolSize=" + std::to_string(min_pool_size) + "&maxPoolSize=" + std::to_string(max_pool_size)),
        client(pool.acquire()), market_data_service_db((*client)[market_data_handler::market_data_service_db_name]), m_min_pool_size_(min_pool_size),
        m_max_pool_size_(max_pool_size), m_p_logger_(p_logger) {
            LOG_INFO(m_p_logger_, "Mongo URI: {}", str_uri);
        }

        mongocxx::instance inst{};
        std::string str_uri;
        mongocxx::uri uri{str_uri};
        mongocxx::pool pool{uri};
        mongocxx::pool::entry client;
        mongocxx::database market_data_service_db;

    protected:
        const int m_min_pool_size_;
        const int m_max_pool_size_;
        quill::Logger* m_p_logger_;
    };
}
