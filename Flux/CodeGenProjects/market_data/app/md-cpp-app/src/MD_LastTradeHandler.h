#pragma once

#include "MD_TopOfBookPublisher.h"
#include "MD_LastTrade.h"


namespace md_handler{

    class MD_LastTradeHandler{
    public:
        explicit MD_LastTradeHandler(MD_MongoDBHandler &mongo_db_, const bool no_aggregate_ = true)
        :mongo_db(mongo_db_), no_aggregate(no_aggregate_) {
            UpdateTopOfBookCache_();
        }

        void handle_mkt_overview(md_handler::MD_MktOverview &mkt_overview){
            auto& last_trade_data = mkt_overview.getLastTrade();

            bsoncxx::document::view_or_value last_trade_document = bsoncxx::builder::stream::document{}
                << symbol_key << last_trade_data.getSymbol()
                << time_key << bsoncxx::types::b_date(get_chrono_ms_from_int64(last_trade_data.getMillisecondsSinceEpoch()))
                << px_key << last_trade_data.getPx()
                << qty_key << last_trade_data.getQty()
                << exchange_key << last_trade_data.getExchange()
                << "special_conditions" << last_trade_data.getSpecialConditions()
                << "past_limit" << last_trade_data.getPastLimit()
                << "unreported" << last_trade_data.getUnreported()
                << bsoncxx::builder::stream::finalize;
            auto last_trade_result = last_trade_collection.insert_one(last_trade_document);

            if(no_aggregate){
                std::string dbId = md_handler::MD_TopOfBookPublisher::GetDBIdForSymbol(last_trade_data.getSymbol());
                if (not dbId.empty()){
                    top_of_book_publisher.patch_data(dbId, mkt_overview);
                }
                else{
                    top_of_book_publisher.create_data(mkt_overview);
                }
            }
            else{
                mongocxx::pipeline pipeline{};
                update_pipeline(pipeline, 10.0);
                auto last_trade_aggregate_result = last_trade_collection.aggregate(pipeline,
                                                                                   mongocxx::options::aggregate{});
                // The loop just helps commit - without this commit does not trigger - though the code never enters loop
                for (auto &last_trade_: last_trade_aggregate_result) {}


                for (auto& last_trade_doc: last_trade_collection.find({})){
                    auto time_in_ms =  last_trade_data.getMillisecondsSinceEpoch(); // (bsoncxx::types::b_date(get_chrono_ms_from_int64())).to_int64();
                    const std::string &symbol = last_trade_doc[symbol_key].get_string().value.data();
                    int64_t participation_period_last_trade_qty_sum;
                    if (bsoncxx::type::k_int32 == last_trade_doc["market_trade_volume"]["participation_period_last_trade_qty_sum"].type()){
                        participation_period_last_trade_qty_sum = last_trade_doc["market_trade_volume"]["participation_period_last_trade_qty_sum"].get_int32().value;
                    }
                    else{
                        participation_period_last_trade_qty_sum = last_trade_doc["market_trade_volume"]["participation_period_last_trade_qty_sum"].get_int64().value;
                    }
                    md_handler::MD_LastTrade aggregated_last_trade_data(symbol,
                                                                        last_trade_doc[px_key].get_double().value,
                                                                        last_trade_doc[qty_key].get_int64().value,
                                                                        time_in_ms, "", "", false, false,
                                                                        participation_period_last_trade_qty_sum,
                                                                        10);
                    md_handler::MD_MktOverview agg_mkt_overview(aggregated_last_trade_data, mkt_overview.getTotalTradingSecSize());
                    std::string dbId = md_handler::MD_TopOfBookPublisher::GetDBIdForSymbol(symbol);
                    if (not dbId.empty()){
                        top_of_book_publisher.patch_data(dbId,
                                                         agg_mkt_overview);
                    }
                    else{
                        top_of_book_publisher.create_data(agg_mkt_overview);
                    }
                }
            }
        }

        void handle_last_trade_update(md_handler::MD_LastTrade &last_trade_data){
            md_handler::MD_MktOverview mkt_overview(last_trade_data, 0);
            handle_mkt_overview(mkt_overview);
        }

    protected:
        MD_TopOfBookPublisher top_of_book_publisher;
        MD_MongoDBHandler &mongo_db;
        const bool no_aggregate;
        mongocxx::collection top_of_book_collection = mongo_db.market_data_db[top_of_book];
        mongocxx::collection last_trade_collection = mongo_db.market_data_db[last_trade];

        void UpdateTopOfBookCache_(){
            for (auto &&top_of_book_document: top_of_book_collection.find({})) {
                std::ostringstream key_builder;
                const std::string symbol = top_of_book_document["symbol"].get_string().value.data();
                const std::string str_id = top_of_book_document["_id"].get_oid().value.to_string();
                md_handler::MD_TopOfBookPublisher::UpdateTopOfBookCache(symbol, str_id);
            }

        }

        //buggy - last trade qty sum has to be computed per symbol - not used for now - fix before use
        void _init_overall_last_trade_qty_sum() {
            long overall_last_trade_qty_sum = 0;
            auto order = bsoncxx::builder::stream::document{} << "_id" << -1 << bsoncxx::builder::stream::finalize;
            auto opts = mongocxx::options::find{};
            opts.sort(order.view()).limit(1);
            auto last_trade_doc_cursor = last_trade_collection.find({}, opts);
            for (auto &&last_trade_doc: last_trade_doc_cursor) {
                if (bsoncxx::type::k_int32 ==
                    last_trade_doc["market_trade_volume"]["participation_period_last_trade_qty_sum"].type()) {
                    overall_last_trade_qty_sum = last_trade_doc["market_trade_volume"]["participation_period_last_trade_qty_sum"].get_int32().value;
                } else {
                    overall_last_trade_qty_sum = last_trade_doc["market_trade_volume"]["participation_period_last_trade_qty_sum"].get_int64().value;
                }
            }
        }

        // n_sec defined period of time to aggregate the volume sum
        static void update_pipeline(mongocxx::pipeline &pipeline, int64_t n_sec) {
            static const std::string dollar_qty_key = "$" + qty_key;
            static const std::string dollar_px_key = "$" + px_key;
            static const std::string dollar_symbol_key = "$" + symbol_key;

            pipeline.append_stage(make_document(
                    kvp("$setWindowFields", make_document(
                            kvp("partitionBy", make_document(
                                    kvp("symbol", dollar_symbol_key)
            )),
            kvp("sortBy", make_document(
                    kvp("time", 1)
            )),
                kvp("output", make_document(
                    kvp("market_trade_volume.participation_period_last_trade_qty_sum", make_document(
                        kvp("$sum", "$qty"),
                        kvp("window", make_document(
                            kvp("range", make_array(-n_sec, "current")),
                            kvp("unit", "second")
                        ))
                    ))
                ))
            ))));

            pipeline.append_stage(make_document(
                kvp("$merge", make_document(
                    kvp("into", last_trade),
                    kvp("on", "_id"),
                    kvp("whenMatched", "replace"),
                    kvp("whenNotMatched", "insert")
                ))
            ));
        }
    };
}


