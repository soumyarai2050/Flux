#pragma once

#include <Python.h>
#include <iostream>
#include <mobile_book_service.pb.h>

#include "market_depth_handler.h"
#include "last_trade_handler.h"
#include "mongo_db_codec.h"
#include "mongo_db_singleton.h"

extern "C" void create_or_update_md_n_tob(const int32_t id, const char* symbol, const char* exch_time, const char* arrival_time,
                                          const int side, const int32_t position, const float px = mobile_book, const int64_t qty = mobile_book,
                                          const float premium = mobile_book, const char* market_maker = "", const bool is_smart_depth = false,
                                          const float cumulative_notional = mobile_book, const int64_t cumulative_qty = mobile_book,
                                          const float cumulative_avg_px = mobile_book) {

    std::cout << "Side: " << side << std::endl;

    mobile_book::TickType k_side;
    if (side == 1) {
        k_side = mobile_book::TickType::BID;
    } else if (side == 2) {
        k_side = mobile_book::TickType::ASK;
    }

    std::cout << k_side << std::endl;
    std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db = MongoDBHandlerSingleton::get_instance();
    mobile_book_handler::MarketDepthHandler marketDepthHandler(sp_mongo_db);
//    marketDepthHandler.update_market_depth_cache_();
//    marketDepthHandler.update_top_of_book_cache_();

    mobile_book::MarketDepth market_depth;
    market_depth.set_id(id);
    market_depth.set_symbol(symbol);
    market_depth.set_exch_time(exch_time);
    market_depth.set_arrival_time(arrival_time);
    market_depth.set_side(k_side);
    market_depth.set_px(px);
    market_depth.set_qty(qty);
    market_depth.set_premium(premium);
    market_depth.set_position(position);
    market_depth.set_market_maker(market_maker);
    market_depth.set_is_smart_depth(is_smart_depth);
    market_depth.set_cumulative_notional(cumulative_notional);
    market_depth.set_cumulative_qty(cumulative_qty);
    market_depth.set_cumulative_avg_px(cumulative_avg_px);

    marketDepthHandler.handle_md_update(market_depth);
}



extern "C" void create_or_update_last_trade_n_tob(const int32_t id, const char* symbol, const char* exch_id, const char* exch_time,
                                                 const char* arrival_time, const float px, const int64_t qty, const float premium = mobile_book,
                                                 const char* market_trade_volume_id = "", const int64_t participation_period_last_trade_qty_sum = mobile_book,
                                                 const int32_t applicable_period_seconds = mobile_book) {

    std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db = MongoDBHandlerSingleton::get_instance();
    mobile_book_handler::LastTradeHandler lastTradeHandler(sp_mongo_db);

    mobile_book::LastTrade last_trade;
    last_trade.set_id(id);
    last_trade.set_px(px);
    last_trade.set_qty(qty);
    last_trade.set_premium(premium);
    last_trade.set_exch_time(exch_time);
    last_trade.set_arrival_time(arrival_time);
    last_trade.mutable_symbol_n_exch_id()->set_symbol(symbol);
    last_trade.mutable_symbol_n_exch_id()->set_exch_id(exch_id);
    last_trade.mutable_market_trade_volume()->set_id(market_trade_volume_id);
    last_trade.mutable_market_trade_volume()->set_participation_period_last_trade_qty_sum(participation_period_last_trade_qty_sum);
    last_trade.mutable_market_trade_volume()->set_applicable_period_seconds(applicable_period_seconds);

    lastTradeHandler.handle_last_trade_update(last_trade);
}
