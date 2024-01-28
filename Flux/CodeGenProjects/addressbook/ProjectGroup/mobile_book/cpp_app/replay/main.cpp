#include "last_trade_handler.h"
#include "market_depth_handler.h"
#include "history_manager.h"
#include "../../../../../../FluxCppCore/include/mongo_db_handler.h"

int main() {

    std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db =
            std::make_shared<FluxCppCore::MongoDBHandler>();
    mobile_book_handler::MarketDepthHandler marketDepthHandler(sp_mongo_db);
    mobile_book_handler::LastTradeHandler lastTradeHandler(sp_mongo_db);
    mobile_book_handler::HistoryManager historyManager(sp_mongo_db, lastTradeHandler, marketDepthHandler);
    historyManager.replay();

    return 0;
}

