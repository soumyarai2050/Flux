#include "MD_MongoDBHandler.h"
#include "MD_HistoryManager.h"
#include "MD_LastTradeHandler.h"
#include "MD_DepthHandler.h"

int main()
{
    md_handler::MD_MongoDBHandler mongo_db;
    md_handler::MD_DepthHandler marketDepthHandler(mongo_db);
    md_handler::MD_LastTradeHandler lastTradeHandler(mongo_db);
    md_handler::MD_HistoryManager marketDataHistoryManager(mongo_db, marketDepthHandler, lastTradeHandler);
    marketDataHistoryManager.replay(md_handler::ReplyType::NOW_ACCELERATE);
    return 0;
}
