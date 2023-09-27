#include "last_trade_handler.h"
#include "market_depth_handler.h"
#include "history_manager.h"

int main() {

    std::shared_ptr<market_data_handler::MarketData_MongoDBHandler> sp_mongo_db =
            std::make_shared<MarketData_MongoDBHandler>();
    market_data_handler::MarketDepthHandler marketDepthHandler(sp_mongo_db);
    market_data_handler::LastTradeHandler lastTradeHandler(sp_mongo_db);
    market_data_handler::HistoryManager historyManager(sp_mongo_db, lastTradeHandler, marketDepthHandler);
    historyManager.replay();

    return 0;
}

