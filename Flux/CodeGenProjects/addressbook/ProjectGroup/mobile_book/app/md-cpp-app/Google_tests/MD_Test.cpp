#include <utility>

#include "gtest/gtest.h"

#include "../../cpp_app/replay/market_depth_handler.h"
#include "../../cpp_app/replay/last_barter_handler.h"
#include "mobile_book_mongo_db_handler.h"
#include "mongo_db_codec.h"

namespace md_test{
    static const std::string symbol = "RY";
    std::shared_ptr<mobile_book_handler::MobileBook_MongoDBHandler> sp_mongo_db =
            std::make_shared<mobile_book_handler::MobileBook_MongoDBHandler>();
    FluxCppCore::MongoDBCodec<mobile_book::LastBarter, mobile_book::LastBarterList> lastBarterCodec(sp_mongo_db);
    FluxCppCore::MongoDBCodec<mobile_book::MarketDepth, mobile_book::MarketDepthList> marketDepthCodec(sp_mongo_db);
    FluxCppCore::MongoDBCodec<mobile_book::TopOfBook, mobile_book::TopOfBookList> topOfBookHandler(sp_mongo_db);
}

using namespace md_test;

TEST(MobileBookHandlerTestSuite, StartUpTest){ // 12/2/2020 -> 737761
    EXPECT_EQ(marketDepthCodec.get_md_key_to_db_id_size(), 0);
}

TEST(MobileBookHandlerTestSuite, DeleteManyMarketDepthTest) {
    // delete all specific symbol and side (defined in bid_query / ask_query ) documents and validate
    bsoncxx::builder::stream::document bid_query;
    mobile_book_handler::get_symbol_side_query(md_test::symbol, "BID", bid_query);

    marketDepthCodec.delete_all_data_from_collection(bid_query);
    auto market_depth_bid_docs_count = marketDepthCodec.count_data_from_collection(bid_query);
    ASSERT_EQ(market_depth_bid_docs_count, 0);

    bsoncxx::builder::stream::document ask_query;
    mobile_book_handler::get_symbol_side_query(symbol, "ASK", ask_query);

    auto market_depth_ask_docs_count = marketDepthCodec.count_data_from_collection(ask_query);
    ASSERT_EQ(market_depth_ask_docs_count, 0);

    // delete all documents in collection and validate
    marketDepthCodec.delete_all_data_from_collection();
    auto market_depth_all_docs_count = marketDepthCodec.count_data_from_collection();
    ASSERT_EQ(market_depth_all_docs_count, 0);
}

TEST(MobileBookHandlerTestSuite, DeleteManyLastBarterTest) {
    // delete all specific symbol and side (defined in bid_query / ask_query ) documents and validate
    lastBarterCodec.delete_all_data_from_collection();
    auto last_barter_docs_count = lastBarterCodec.count_data_from_collection();
    ASSERT_EQ(last_barter_docs_count, 0);
}

TEST(MobileBookHandlerTestSuite, DeleteManyTopOfBookTest) {
    // delete all specific symbol and side (defined in bid_query / ask_query ) documents and validate
    topOfBookHandler.delete_all_data_from_collection();
    auto top_of_book_docs_count = topOfBookHandler.count_data_from_collection();
    ASSERT_GE(top_of_book_docs_count, 0);
}

TEST(MobileBookHandlerTestSuite, AggregateMarketDepthTest){ // 12/2/2020 -> 737761

    mobile_book_handler::MarketDepthHandler marketDepthHandler(sp_mongo_db);
    mobile_book::MarketDepthList market_depth_list;
    mobile_book::MarketDepth market_depth;

    // insert test data into DB (both bid and ask)
    for (int i = 1; i <= 5; ++i) {
        mobile_book_handler::MobileBookPopulateRandomValues::market_depth(market_depth);
        market_depth.set_id(i);
        market_depth.set_symbol(symbol);
        market_depth.set_position(i-1);
        market_depth_list.add_market_depth()->CopyFrom(market_depth);
    }

    for (int i = 0; i < market_depth_list.market_depth_size(); ++i) {
        mobile_book::MarketDepth test_data = market_depth_list.market_depth(i);
        marketDepthHandler.handle_md_update(test_data);
    }

    mobile_book::MarketDepthList db_data;
    marketDepthCodec.get_all_data_from_collection(db_data);

    ASSERT_EQ(market_depth_list.DebugString(), db_data.DebugString());
}

TEST(MobileBookHandlerTestSuite, AggregateTickByTickAllLastTest){ // 12/2/2020 -> 737761

    mobile_book_handler::LastBarterHandler lastBarterHandler(sp_mongo_db);
    mobile_book::LastBarterList last_barter_list;
    mobile_book::LastBarter last_barter;

    for (int i = 1; i <= 5; ++i) {
        mobile_book_handler::MobileBookPopulateRandomValues::last_barter(last_barter);
        last_barter.set_id(i);
        last_barter_list.add_last_barter()->CopyFrom(last_barter);
    }

    for (int i = 0; i < last_barter_list.last_barter_size(); ++i) {
        mobile_book::LastBarter test_data = last_barter_list.last_barter(i);
        lastBarterHandler.handle_last_barter_update(test_data);
    }

    mobile_book::LastBarterList db_data;
    lastBarterCodec.get_all_data_from_collection(db_data);

    ASSERT_EQ(last_barter_list.DebugString(), db_data.DebugString());
}
