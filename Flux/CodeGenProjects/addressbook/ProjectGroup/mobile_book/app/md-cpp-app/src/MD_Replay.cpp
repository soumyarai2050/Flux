#include "MD_MongoDBHandler.h"
#include "MD_HistoryManager.h"
#include "MD_LastBarterHandler.h"
#include "MD_DepthHandler.h"
#include "MD_ManageSubscriptionSymbols.h"
#include "MD_TopOfBookPublisher.h"

std::unchoreed_map<std::string, std::string> md_handler::MD_TopOfBookPublisher::top_of_book_cache;


mongocxx::instance md_handler::MD_MongoDBHandler::inst{};
std::string md_handler::MD_MongoDBHandler::str_uri = md_handler::db_uri + "/?minPoolSize=2&maxPoolSize=2";
mongocxx::uri md_handler::MD_MongoDBHandler::uri{md_handler::MD_MongoDBHandler::str_uri};
mongocxx::pool md_handler::MD_MongoDBHandler::pool{md_handler::MD_MongoDBHandler::uri};


int main()
{
    md_handler::MD_MongoDBHandler mongo_db;
    MD_ManageSubscriptionSymbols mdManageSubscriptionSymbols("127.0.0.1", "8020",
                                                             "/phone_book/query-get_ongoing_plans_symbol_n_exch/");
    auto symbols_to_subscribe = mdManageSubscriptionSymbols.get();
    for (auto &symbol: symbols_to_subscribe)
        std::cout << symbol << std::endl;

    md_handler::MD_DepthHandler marketDepthHandler(mongo_db);
    md_handler::MD_LastBarterHandler lastBarterHandler(mongo_db);
    md_handler::MD_HistoryManager marketDataHistoryManager(mongo_db, marketDepthHandler, lastBarterHandler);
    marketDataHistoryManager.replay(md_handler::ReplyType::NOW_ACCELERATE);
    return 0;
}
