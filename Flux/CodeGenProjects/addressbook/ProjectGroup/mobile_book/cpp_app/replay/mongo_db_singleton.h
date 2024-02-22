#pragma once

#include "mongo_db_handler.h"

class MongoDBHandlerSingleton {
private:
    static std::shared_ptr<FluxCppCore::MongoDBHandler> instance;

    MongoDBHandlerSingleton() {} // Private constructor to prevent instantiation

public:
    static std::shared_ptr<FluxCppCore::MongoDBHandler> get_instance() {
        if (!instance) {
            instance = std::make_shared<FluxCppCore::MongoDBHandler>();
        }
        return instance;
    }
};

std::shared_ptr<FluxCppCore::MongoDBHandler> MongoDBHandlerSingleton::instance = nullptr;