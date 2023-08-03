#pragma once

#include <unordered_map>

#include <bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/json.hpp>
#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>
#include <mongocxx/pool.hpp>

#include "../../generated/CppUtilGen/market_data_constants.h"
#include "quill/Quill.h"

namespace market_data_handler {

    using bsoncxx::builder::basic::make_array;
    using bsoncxx::builder::basic::make_document;
    using bsoncxx::builder::basic::kvp;

    inline void get_symbol_side_query(const std::string &symbol, const std::string &side, bsoncxx::builder::stream::document &query_out){
        query_out << security_fld_name << symbol << side_fld_name << side
                  << bsoncxx::builder::stream::finalize;
    }

    class MarketData_MongoDBHandler {
    public:
        MarketData_MongoDBHandler(quill::Logger* logger, const int min_pool_size = 2, const int max_pool_size = 2):
        str_uri(db_uri + "/?minPoolSize=" + std::to_string(min_pool_size) + "&maxPoolSize=" + std::to_string(max_pool_size)),
        client(pool.acquire()), market_data_service_db((*client)[market_data_service_db_name]), min_pool_size_(min_pool_size),
        max_pool_size_(min_pool_size_), logger_(logger) {
            LOG_INFO(logger_, "Mongo URI: {}", str_uri);
        }

        mongocxx::instance inst{};
        std::string str_uri;
        mongocxx::uri uri{str_uri};
        mongocxx::pool pool{uri};
        mongocxx::pool::entry client;
        mongocxx::database market_data_service_db;

    protected:
        const int min_pool_size_;
        const int max_pool_size_;
        quill::Logger* logger_;
    };
}
