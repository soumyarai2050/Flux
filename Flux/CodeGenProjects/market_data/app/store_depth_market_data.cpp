#include "store_depth_market_data.h"

int main()
{
    MongoDB mongo_db;
    MarketDataHandler marketDataHandler(mongo_db);
    MarketDataHistoryManager marketDataHistoryManager(mongo_db, marketDataHandler);
    marketDataHistoryManager.replay();
}
