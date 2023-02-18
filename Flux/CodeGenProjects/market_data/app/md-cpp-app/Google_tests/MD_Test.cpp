#include <utility>

#include "gtest/gtest.h"
#include "../src/MD_MongoDBHandler.h"
#include "../src/MD_MarketDepth.h"
#include "../src/MD_LastTradeHandler.h"
#include "../src/MD_DepthHandler.h"
#include "../src/MD_Utils.h"

namespace md_test{
    static const std::string symbol = "RY";
    static auto bid_query = md_handler::get_symbol_side_query(symbol, "BID");
    static auto ask_query = md_handler::get_symbol_side_query(symbol, "ASK");
    static md_handler::MD_MongoDBHandler mongo_db;
    static md_handler::MD_DepthHandler marketDataHandler(mongo_db);
    static auto market_depth_collection = mongo_db.market_data_db[md_handler::market_depth];
    static auto last_trade_collection = mongo_db.market_data_db[md_handler::last_trade];
    static auto top_of_book_collection = mongo_db.market_data_db[md_handler::top_of_book];
}

using namespace md_test;

TEST(MarketDataHandlerTestSuite, StartUpTest){ // 12/2/2020 -> 737761
    EXPECT_EQ(marketDataHandler.get_md_key_to_pipeline_n_db_id_size(),0);
}

void validate_db_record_against_expected(const bsoncxx::document::value &query,
                                         const std::vector<md_handler::MD_MarketDepth> &expected_market_depth_record,
                                         const bool ignore_date_time){
    sleep(1); // it seems commits may not reflect immediately - adding delay ensure test case does not fail due to the data visibility delay
    auto db_market_depth_records = market_depth_collection.find({query});
    int i = 0;
    for (const auto &db_market_depth_record: db_market_depth_records) {
        ASSERT_EQ(db_market_depth_record[md_handler::qty_key].get_int64(), expected_market_depth_record[i].getQty());
        ASSERT_EQ(db_market_depth_record[md_handler::px_key].get_double().value, expected_market_depth_record[i].getPx());
        ASSERT_EQ(db_market_depth_record["cumulative_qty"].get_int64().value, expected_market_depth_record[i].getCumulativeQty());
        ASSERT_EQ(db_market_depth_record["cumulative_notional"].get_double().value, expected_market_depth_record[i].getCumulativeNotional());
        ASSERT_EQ(db_market_depth_record["cumulative_avg_px"].get_double().value, expected_market_depth_record[i].getCumulativeAvgPx());
        if(!ignore_date_time){
            //TODO validate date time
        }
        i++;
    }
    ASSERT_EQ(i, expected_market_depth_record.size());
}

void validate_last_trade_records_against_expected(const std::vector<md_handler::MD_LastTrade> &expected_last_trade_record,
                                                  const bool ignore_date_time){
    sleep(1);
    auto last_trade_records = last_trade_collection.find({});
    int i = 0;
    for (auto&& last_trade_record: last_trade_records) {
        ASSERT_EQ(last_trade_record[md_handler::qty_key].get_int64().value, expected_last_trade_record[i].getQty());
        ASSERT_EQ(last_trade_record[md_handler::px_key].get_double().value, expected_last_trade_record[i].getPx());
        ASSERT_EQ(last_trade_record["last_n_sec_total_qty"].get_int32().value,
                  expected_last_trade_record[i].getLastTradeQtySum());
        ASSERT_EQ(last_trade_record["past_limit"].get_bool().value, expected_last_trade_record[i].getPastLimit());
        ASSERT_EQ(last_trade_record["unreported"].get_bool().value, expected_last_trade_record[i].getUnreported());
        if(!ignore_date_time){
            //TODO validate date time
        }
        ++i;
    }
    ASSERT_EQ(i, expected_last_trade_record.size());
}

TEST(MarketDataHandlerTestSuite, DeleteManyMarketDepthTest) {
    // delete all specific symbol and side (defined in bid_query / ask_query ) documents and validate
    market_depth_collection.delete_many({bid_query});
    auto market_depth_bid_docs_count = market_depth_collection.count_documents({bid_query});
    ASSERT_GE(market_depth_bid_docs_count, 0);

    market_depth_collection.delete_many({ask_query});
    auto market_depth_ask_docs_count = market_depth_collection.count_documents({ask_query});
    ASSERT_GE(market_depth_ask_docs_count, 0);

    // delete all documents in collection and validate
    market_depth_collection.delete_many({});
    auto market_depth_all_docs_count = market_depth_collection.count_documents({});
    ASSERT_GE(market_depth_all_docs_count, 0);
}

TEST(MarketDataHandlerTestSuite, DeleteManyLastTradeTest) {
    // delete all specific symbol and side (defined in bid_query / ask_query ) documents and validate
    last_trade_collection.delete_many({});
    auto last_trade_docs_count = last_trade_collection.count_documents({});
    ASSERT_GE(last_trade_docs_count, 0);
}

TEST(MarketDataHandlerTestSuite, DeleteManyTopOfBookTest) {
    // delete all specific symbol and side (defined in bid_query / ask_query ) documents and validate
    top_of_book_collection.delete_many({});
    auto top_of_book_docs_count = top_of_book_collection.count_documents({});
    ASSERT_GE(top_of_book_docs_count, 0);
}

TEST(MarketDataHandlerTestSuite, AggregateMarketDepthTest){ // 12/2/2020 -> 737761

    market_depth_collection.delete_many({});

    std::vector<md_handler::MD_MarketDepth> test_data_list = {{20, 10, 0, symbol, "BID"},
                                                              {30, 5,  1, symbol, "BID"},
                                                              {50, 3,  2, symbol, "BID"},

                                                              {40, 25, 0, symbol, "ASK"},
                                                              {40, 30, 1, symbol, "ASK"}};
    // insert test data into DB (both bid and ask)
    for (auto& test_data: test_data_list){
        md_handler::setMillisecondsSinceEpochNow<md_handler::MD_MarketDepth>(test_data);
        marketDataHandler.handle_md_update(test_data);
    }

    //Create Expected Bid Data:
    std::vector<md_handler::MD_MarketDepth> expected_bid_data_list = {{20, 10, 0, symbol, "BID", 20,  200.0, 10.0},
                                                                      {30, 5,  1, symbol, "BID", 50,  350.0, 7.0},
                                                                      {50, 3,  2, symbol, "BID", 100, 500.0, 5.0}};
    validate_db_record_against_expected(bid_query, expected_bid_data_list, true);

    // Next test : Replace 0th entry in Market Depth and validate all aggregation are as expected
    md_handler::MD_MarketDepth test_data {20, 25, 0, symbol, "BID"};
    md_handler::setMillisecondsSinceEpochNow<md_handler::MD_MarketDepth>(test_data);
    marketDataHandler.handle_md_update(test_data);

    //Create Expected Bid Data:
    std::vector<md_handler::MD_MarketDepth> expected_bid_data_list2 = {{20, 25, 0, symbol, "BID", 20,  500.0, 25.0},
                                                                       {30, 5,  1, symbol, "BID", 50,  650.0, 13.0},
                                                                       {50, 3,  2, symbol, "BID", 100, 800,   8.0}};
    validate_db_record_against_expected(bid_query, expected_bid_data_list2, true);


    // post_insert_ask_market_depths: retrieve only side: ASK data for symbol defined in ask_query
    std::vector<md_handler::MD_MarketDepth> expected_ask_data_list = {{40, 25, 0, symbol, "ASK", 40, 1000.0, 25.0},
                                                                      {40, 30, 1, symbol, "ASK", 80, 2200,   27.5}};
    validate_db_record_against_expected(ask_query, expected_ask_data_list, true);
}

TEST(MarketDataHandlerTestSuite, AggregateTickByTickAllLastTest){ // 12/2/2020 -> 737761

    last_trade_collection.delete_many({});

    static md_handler::MD_LastTradeHandler tickByTickDataHandler(mongo_db);

    std::vector<md_handler::MD_LastTrade> last_trade_data_vector = {{"RY", 10, 10, 0, "USD_A", "SP1", false, false},
                                                                    {"RY", 20, 15, 0, "USD_B", "SP2", false, false},
                                                                    {"RY", 30, 20, 0, "USD_C", "SP3", false, false},
                                                                    {"RY", 40, 30, 0, "USD_D", "SP4", false, false},
                                                                    {"RY", 50, 40, 0, "USD_E", "SP5", false, false}};


    for (auto&& last_trade_data: last_trade_data_vector) {
        md_handler::setMillisecondsSinceEpochNow<md_handler::MD_LastTrade>(last_trade_data);
        tickByTickDataHandler.handle_last_trade_update(last_trade_data);
    }

    std::vector<md_handler::MD_LastTrade> expected_last_trade_data = {{"RY", 10, 10, 0, "USD_A", "SP1", false, false, 10},
                                                                      {"RY", 20, 15, 0, "USD_B", "SP2", false, false, 25},
                                                                      {"RY", 30, 20, 0, "USD_C", "SP3", false, false, 45},
                                                                      {"RY", 40, 30, 0, "USD_D", "SP4", false, false, 75},
                                                                      {"RY", 50, 40, 0, "USD_E", "SP5", false, false, 115}};

    validate_last_trade_records_against_expected(expected_last_trade_data, true);
}
