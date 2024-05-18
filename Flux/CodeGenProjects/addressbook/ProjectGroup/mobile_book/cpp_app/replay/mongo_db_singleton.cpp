#include "mongo_db_singleton.h"

std::shared_ptr<FluxCppCore::MongoDBHandler> MongoDBHandlerSingleton::instance = nullptr;