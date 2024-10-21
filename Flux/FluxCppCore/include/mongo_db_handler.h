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
                         const std::string &kr_db_name,
                         int min_pool_size = market_data_handler::min_pool_size_val,
                         int max_pool_size = market_data_handler::max_pool_size_val)
            : m_instance_(), m_mongo_db_uri_(kr_db_uri + "/?minPoolSize=" + std::to_string(min_pool_size) +
                              "&maxPoolSize=" + std::to_string(max_pool_size)),
              m_mongo_db_name_(kr_db_name),
              m_mongo_uri_(m_mongo_db_uri_),
              m_pool_(m_mongo_uri_) {
            std::cout << "Mongo URI: " << m_mongo_db_uri_ << std::endl;
        }

        // Get a client from the pool
        mongocxx::pool::entry get_pool_client() const {
            std::lock_guard<std::mutex> lock(m_mutex_);
            return m_pool_.acquire();
        }

    protected:
        mongocxx::instance m_instance_;
        std::string m_mongo_db_uri_;
    public:
        std::string m_mongo_db_name_;
    protected:
        mongocxx::uri m_mongo_uri_;
        mutable std::mutex m_mutex_{}; // Protect access to the pool
        mutable mongocxx::pool m_pool_; // Connection pool
    };

}
