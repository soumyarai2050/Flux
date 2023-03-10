#include "MD_MongoDBHandler.h"


mongocxx::instance md_handler::MD_MongoDBHandler::inst{};
std::string md_handler::MD_MongoDBHandler::str_uri = md_handler::db_uri + "/?minPoolSize=2&maxPoolSize=2";
mongocxx::uri md_handler::MD_MongoDBHandler::uri{md_handler::MD_MongoDBHandler::str_uri};
mongocxx::pool md_handler::MD_MongoDBHandler::pool{md_handler::MD_MongoDBHandler::uri};
