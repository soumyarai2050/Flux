#include <utility>

#include "gtest/gtest.h"

#include "../../cpp_app/src/market_depth_handler.h"
#include "../../cpp_app/src/last_trade_handler.h"
#include "market_data_mongo_db_handler.h"
#include "mongo_db_codec.h"

namespace md_test{
    static const std::string symbol = "RY";
    std::shared_ptr<market_data_handler::MarketData_MongoDBHandler> sp_mongo_db =
            std::make_shared<market_data_handler::MarketData_MongoDBHandler>();
    FluxCppCore::MongoDBCodec<market_data::LastTrade, market_data::LastTradeList> lastTradeCodec(sp_mongo_db);
    FluxCppCore::MongoDBCodec<market_data::MarketDepth, market_data::MarketDepthList> marketDepthCodec(sp_mongo_db);
    FluxCppCore::MongoDBCodec<market_data::TopOfBook, market_data::TopOfBookList> topOfBookHandler(sp_mongo_db);
}

using namespace md_test;

TEST(MarketDataHandlerTestSuite, StartUpTest){ // 12/2/2020 -> 737761
    EXPECT_EQ(marketDepthCodec.get_md_key_to_db_id_size(), 0);
}

TEST(MarketDataHandlerTestSuite, DeleteManyMarketDepthTest) {
    // delete all specific symbol and side (defined in bid_query / ask_query ) documents and validate
    bsoncxx::builder::stream::document bid_query;
    market_data_handler::get_symbol_side_query(md_test::symbol, "BID", bid_query);

    marketDepthCodec.delete_all_data_from_collection(bid_query);
    auto market_depth_bid_docs_count = marketDepthCodec.count_data_from_collection(bid_query);
    ASSERT_EQ(market_depth_bid_docs_count, 0);

    bsoncxx::builder::stream::document ask_query;
    market_data_handler::get_symbol_side_query(symbol, "ASK", ask_query);

    auto market_depth_ask_docs_count = marketDepthCodec.count_data_from_collection(ask_query);
    ASSERT_EQ(market_depth_ask_docs_count, 0);

    // delete all documents in collection and validate
    marketDepthCodec.delete_all_data_from_collection();
    auto market_depth_all_docs_count = marketDepthCodec.count_data_from_collection();
    ASSERT_EQ(market_depth_all_docs_count, 0);
}

TEST(MarketDataHandlerTestSuite, DeleteManyLastTradeTest) {
    // delete all specific symbol and side (defined in bid_query / ask_query ) documents and validate
    lastTradeCodec.delete_all_data_from_collection();
    auto last_trade_docs_count = lastTradeCodec.count_data_from_collection();
    ASSERT_EQ(last_trade_docs_count, 0);
}

TEST(MarketDataHandlerTestSuite, DeleteManyTopOfBookTest) {
    // delete all specific symbol and side (defined in bid_query / ask_query ) documents and validate
    topOfBookHandler.delete_all_data_from_collection();
    auto top_of_book_docs_count = topOfBookHandler.count_data_from_collection();
    ASSERT_GE(top_of_book_docs_count, 0);
}

TEST(MarketDataHandlerTestSuite, AggregateMarketDepthTest){ // 12/2/2020 -> 737761

    market_data_handler::MarketDepthHandler marketDepthHandler(sp_mongo_db);
    market_data::MarketDepthList market_depth_list;
    market_data::MarketDepth market_depth;

    // insert test data into DB (both bid and ask)
    for (int i = 1; i <= 5; ++i) {
        market_data_handler::MarketDataPopulateRandomValues::market_depth(market_depth);
        market_depth.set_id(i);
        market_depth.set_symbol(symbol);
        market_depth.set_position(i-1);
        market_depth_list.add_market_depth()->CopyFrom(market_depth);
    }

    for (int i = 0; i < market_depth_list.market_depth_size(); ++i) {
        market_data::MarketDepth test_data = market_depth_list.market_depth(i);
        marketDepthHandler.handle_md_update(test_data);
    }

    market_data::MarketDepthList db_data;
    marketDepthCodec.get_all_data_from_collection(db_data);

    ASSERT_EQ(market_depth_list.DebugString(), db_data.DebugString());
}

TEST(MarketDataHandlerTestSuite, AggregateTickByTickAllLastTest){ // 12/2/2020 -> 737761

    market_data_handler::LastTradeHandler lastTradeHandler(sp_mongo_db);
    market_data::LastTradeList last_trade_list;
    market_data::LastTrade last_trade;

    for (int i = 1; i <= 5; ++i) {
        market_data_handler::MarketDataPopulateRandomValues::last_trade(last_trade);
        last_trade.set_id(i);
        last_trade_list.add_last_trade()->CopyFrom(last_trade);
    }

    for (int i = 0; i < last_trade_list.last_trade_size(); ++i) {
        market_data::LastTrade test_data = last_trade_list.last_trade(i);
        lastTradeHandler.handle_last_trade_update(test_data);
    }

    market_data::LastTradeList db_data;
    lastTradeCodec.get_all_data_from_collection(db_data);

    ASSERT_EQ(last_trade_list.DebugString(), db_data.DebugString());
}
