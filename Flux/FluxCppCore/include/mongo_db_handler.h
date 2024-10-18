#pragma once


#include <bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/json.hpp>
#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>
#include <mongocxx/pool.hpp>

#include "../../generated/CppUtilGen/market_data_constants.h"

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
        explicit MongoDBHandler(const std::string &kr_db_uri,
                                const std::string &_kr_db_name,
                                const int min_pool_size = market_data_handler::min_pool_size_val,
                                const int max_pool_size = market_data_handler::max_pool_size_val):
        str_uri(kr_db_uri + "/?minPoolSize=" + std::to_string(min_pool_size) + "&maxPoolSize=" + std::to_string(max_pool_size)),
        client(pool.acquire()), m_db_name_(_kr_db_name), market_data_service_db((*client)[m_db_name_]),
        m_min_pool_size_(min_pool_size), m_max_pool_size_(max_pool_size) {}

        mongocxx::instance inst{};
        std::string m_mongo_db_uri_;
        std::string str_uri;
        mongocxx::uri uri{str_uri};
        mongocxx::pool pool{uri};
        mongocxx::pool::entry client;
        std::string m_db_name_;
        mongocxx::database market_data_service_db;

    protected:
        const int m_min_pool_size_;
        const int m_max_pool_size_;
    };
}
