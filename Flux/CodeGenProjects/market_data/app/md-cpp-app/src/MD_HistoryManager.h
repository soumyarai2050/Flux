#pragma once

#include <memory>
#include <exception>
#include <chrono>

#include "MD_MarketDepth.h"
#include "MD_DepthHandler.h"
#include "MD_LastTrade.h"
#include "MD_LastTradeHandler.h"
#include "MD_Utils.h"

namespace md_handler {
    enum class ReplyType {
        HISTORY_ACCELERATE,
        NOW_ACCELERATE,
        HISTORY_PROPORTIONATE,
        NOW_PROPORTIONATE,
    };

    template<typename T>
    void setMillisecondsSinceEpoch(T &obj, const bsoncxx::types::b_date &date_time,
                                   const ReplyType replay_type = ReplyType::NOW_ACCELERATE){
        switch(replay_type){
            case ReplyType::HISTORY_ACCELERATE:
                obj.setMillisecondsSinceEpoch(date_time.to_int64());
                break;
            case ReplyType::NOW_ACCELERATE:{
                setMillisecondsSinceEpochNow(obj);
                break;
            }
            default:
                throw std::runtime_error("HISTORY_PROPORTIONATE and NOW_PROPORTIONATE replay type are not supported yet");
        }
    }

    class MD_HistoryManager {
    public:
        MD_HistoryManager(MD_MongoDBHandler &mongo_db_, MD_DepthHandler &marketDataHandler_,
                          MD_LastTradeHandler &lastTradeHandler_)
        :mongo_db(mongo_db_), marketDepthHandler(marketDataHandler_), lastTradeHandler(lastTradeHandler_) {}

        void replay(const ReplyType replay_type=ReplyType::HISTORY_ACCELERATE) {
            auto md_depth_history_doc_itr = md_depth_history_cursor.begin();
            bool market_depth_no_replay = true;
            std::shared_ptr<MD_MarketDepth> sp_market_depth;

            auto all_last_doc_itr = last_trade_cursor.begin();
            bool all_last_no_replay = true;
            std::shared_ptr<MD_LastTrade> sp_last_trade;

            while(true){
                if(md_depth_history_doc_itr != md_depth_history_cursor.end()){
                    if (market_depth_no_replay){
                        auto &&md_depth_history_doc = *md_depth_history_doc_itr;
                        sp_market_depth = std::make_shared<MD_MarketDepth>(md_depth_history_doc[qty_key].get_int64().value,
                                                         md_depth_history_doc[px_key].get_double().value,
                                                         static_cast<int8_t>(md_depth_history_doc[position_key].get_int32().value),
                                                         md_depth_history_doc[symbol_key].get_string().value.data(),
                                                         md_depth_history_doc[side_key].get_string().value.data());
                        bsoncxx::types::b_date date_time = md_depth_history_doc[time_key].get_date();
                        setMillisecondsSinceEpoch<MD_MarketDepth>(*sp_market_depth, date_time, replay_type);
                        market_depth_no_replay = false;
                        md_depth_history_doc_itr++;
                    }
                }

                if(all_last_doc_itr != last_trade_cursor.end()){
                    if(all_last_no_replay){
                        auto &all_last_document = *all_last_doc_itr;
                        sp_last_trade = std::make_shared<MD_LastTrade>(all_last_document[symbol_key].get_string().value.data(),
                                                                       all_last_document[px_key].get_double().value,
                                                                       all_last_document[qty_key].get_int64().value);
                        bsoncxx::types::b_date date_time = all_last_document[time_key].get_date();
                        setMillisecondsSinceEpoch<MD_LastTrade>(*sp_last_trade, date_time, replay_type);
                        all_last_no_replay = false;
                        all_last_doc_itr++;
                    }
                }
                //now replay if data is there , replay whichever is reverse chronologically first
                bool replay_done_this_iteration = false;
                if(!market_depth_no_replay){
                    if (all_last_no_replay ||
                    sp_market_depth->getMillisecondsSinceEpoch() > sp_last_trade->getMillisecondsSinceEpoch()){
                        marketDepthHandler.handle_md_update(*sp_market_depth);
                        market_depth_no_replay = true;
                        replay_done_this_iteration = true;
                    }
                }
                if(!replay_done_this_iteration and !all_last_no_replay){
                    lastTradeHandler.handle_last_trade_update(*sp_last_trade);
                    all_last_no_replay = true;
                    replay_done_this_iteration = true;
                }
                //else not needed
                if(not replay_done_this_iteration) // nothing left to replay
                    break;
            }
        }

    protected:
        MD_MongoDBHandler &mongo_db;
        MD_DepthHandler &marketDepthHandler;
        MD_LastTradeHandler &lastTradeHandler;
        mongocxx::collection market_depth_history_collection{mongo_db.market_data_db[market_data_history]};
        mongocxx::collection last_trade_collection{mongo_db.market_data_db[last_trade]};
        // creating cursor for MarketDepthHistory and TickByTickAllLast collections
        mongocxx::cursor md_depth_history_cursor = market_depth_history_collection.find({});
        mongocxx::cursor last_trade_cursor = last_trade_collection.find({});
    };
}

