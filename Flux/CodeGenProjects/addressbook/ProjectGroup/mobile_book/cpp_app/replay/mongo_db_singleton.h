#pragma once

#include "mongo_db_handler.h"

class MongoDBHandlerSingleton {
private:
    static std::shared_ptr<FluxCppCore::MongoDBHandler> instance;

    MongoDBHandlerSingleton() {} // Private constructor to prevent instantiation

public:
    static std::shared_ptr<FluxCppCore::MongoDBHandler> get_instance(const std::string &kr_db_uri = mobile_book_handler::db_uri,
                                                                     const std::string &_kr_db_name = mobile_book_handler::mobile_book_service_db_name,
                                                                     quill::Logger* p_logger = quill::get_logger(),
                                                                     const int min_pool_size = mobile_book_handler::min_pool_size_val,
                                                                     const int max_pool_size = mobile_book_handler::max_pool_size_val) {
        if (!instance) {
            instance = std::make_shared<FluxCppCore::MongoDBHandler>(kr_db_uri, _kr_db_name, p_logger, min_pool_size, max_pool_size);
        }
        return instance;
    }
};

