#include "MD_MongoDBHandler.h"
#include "MD_HistoryManager.h"
#include "MD_LastTradeHandler.h"
#include "MD_DepthHandler.h"
#include "MD_WebSocketServer.h"
#include "MD_ManageSubscriptionSymbols.h"

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

    WebsocketServer websocketServer;
    websocketServer.run();

    return 0;
}

