#include "MD_MongoDBHandler.h"
#include "MD_HistoryManager.h"
#include "MD_LastTradeHandler.h"
#include "MD_DepthHandler.h"
#include "MD_ManageSubscriptionSymbols.h"
#include "MD_TopOfBookPublisher.h"

std::unordered_map<std::string, std::string> md_handler::MD_TopOfBookPublisher::top_of_book_cache;


mongocxx::instance md_handler::MD_MongoDBHandler::inst{};
std::string md_handler::MD_MongoDBHandler::str_uri = md_handler::db_uri + "/?minPoolSize=2&maxPoolSize=2";
mongocxx::uri md_handler::MD_MongoDBHandler::uri{md_handler::MD_MongoDBHandler::str_uri};
mongocxx::pool md_handler::MD_MongoDBHandler::pool{md_handler::MD_MongoDBHandler::uri};


int main()
{
    md_handler::MD_MongoDBHandler mongo_db;
    MD_ManageSubscriptionSymbols mdManageSubscriptionSymbols("127.0.0.1", "8020",
                                                             "/pair_strat_engine/query-get_ongoing_strats/");
    auto symbols_to_subscribe = mdManageSubscriptionSymbols.get();
    for (auto &symbol: symbols_to_subscribe)
        std::cout << symbol << std::endl;
    md_handler::MD_DepthHandler marketDepthHandler(mongo_db);
    md_handler::MD_LastTradeHandler lastTradeHandler(mongo_db);
    md_handler::MD_HistoryManager marketDataHistoryManager(mongo_db, marketDepthHandler, lastTradeHandler);
    marketDataHistoryManager.replay(md_handler::ReplyType::NOW_ACCELERATE);
    return 0;
}

