#pragma once

#include <Python.h>
#include <iostream>
#include <mobile_book_service.pb.h>

#include "market_depth_handler.h"
#include "last_barter_handler.h"
#include "mongo_db_codec.h"
#include "mongo_db_singleton.h"
#include "mobile_book_cache.h"
#include "utility_functions.h"

static mobile_book::TopOfBook top_of_book_obj;
static mobile_book::LastBarter last_barter_obj;
static mobile_book::MarketDepth market_depth_obj;

static int32_t tob_ws_port = FluxCppCore::find_free_port();
static int32_t md_ws_port = FluxCppCore::find_free_port();
static int32_t lt_ws_port = FluxCppCore::find_free_port();

static MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook> tob_websocket_server_(top_of_book_obj, host, tob_ws_port, 36000);
static MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> lt_websocket_server_(last_barter_obj, host, lt_ws_port, 36000);
static MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> md_websocket_server_(market_depth_obj, host, md_ws_port, 36000);
static std::thread m_top_of_book_websocket_thread_{[](){tob_websocket_server_.run();}};
static std::thread m_last_barter_websocket_thread_{[](){lt_websocket_server_.run();}};
static std::thread m_market_depth_websocket_thread_{[](){md_websocket_server_.run();}};


extern "C" void initialize_database(const char* db_uri, const char* db_name, PyObject* port_dict) {
    // Acquire the GIL
    PyGILState_STATE gstate = PyGILState_Ensure();

    // Your existing code to initialize the database
    auto sp_mongo_db = MongoDBHandlerSingleton::get_instance(db_uri, db_name);

    // Update the port dictionary
    PyDict_SetItemString(port_dict, top_of_book_port_key.c_str(), PyLong_FromLong(tob_ws_port));
    PyDict_SetItemString(port_dict, market_depth_port_key.c_str(), PyLong_FromLong(md_ws_port));
    PyDict_SetItemString(port_dict, last_barter_port_key.c_str(), PyLong_FromLong(lt_ws_port));

    // Release the GIL
    PyGILState_Release(gstate);
}

extern "C" void create_or_update_md_n_tob(const int32_t id, const char* symbol,
                                          const char* exch_time, const char* arrival_time, const int side,
                                          const int32_t position, const float px = 0, const int64_t qty = 0,
                                          const char* market_maker = "", const bool is_smart_depth = false,
                                          const float cumulative_notional = 0, const int64_t cumulative_qty = 0,
                                          const float cumulative_avg_px = 0) {

    std::cout << "create_or_update_md_n_tob" << std::endl;
    static mobile_book_cache::MarketDepthCache marketDepthCache;
    static mobile_book_cache::TopOfBookCache topOfBookCache;
    auto sp_mongo_db = MongoDBHandlerSingleton::get_instance();
    TopOfBookHandler topOfBookHandler(sp_mongo_db, tob_websocket_server_);
    MarketDepthHandler market_depth_handler(sp_mongo_db, md_websocket_server_, topOfBookHandler, marketDepthCache, topOfBookCache);

    mobile_book::TickType k_side;
    if (side == 1) {
        k_side = mobile_book::TickType::BID;
    } else if (side == 2) {
        k_side = mobile_book::TickType::ASK;
    }

    mobile_book::MarketDepth market_depth;
    market_depth.set_id(id);
    market_depth.set_symbol(symbol);
    market_depth.set_exch_time(exch_time);
    market_depth.set_arrival_time(arrival_time);
    market_depth.set_side(k_side);
    market_depth.set_px(px);
    market_depth.set_qty(qty);
//    market_depth.set_premium(premium);
    market_depth.set_position(position);
    market_depth.set_market_maker(market_maker);
    market_depth.set_is_smart_depth(is_smart_depth);
    market_depth.set_cumulative_notional(cumulative_notional);
    market_depth.set_cumulative_qty(cumulative_qty);
    market_depth.set_cumulative_avg_px(cumulative_avg_px);

    market_depth_handler.handle_md_update(market_depth);
    std::cout << "create_or_update_md_n_tob end" << std::endl;
}



extern "C" void create_or_update_last_barter_n_tob(const int32_t id, const char* symbol, const char* exch_id, const char* exch_time,
                                                 const char* arrival_time, const float px, const int64_t qty, const float premium = 0,
                                                 const char* market_barter_volume_id = "", const int64_t participation_period_last_barter_qty_sum = 0,
                                                 const int32_t applicable_period_seconds = 0) {


    std::cout << "create_or_update_last_barter_n_tob" << std::endl;
    mobile_book_cache::TopOfBookCache topOfBookCache;
    mobile_book_cache::LastBarterCache lastBarterCache;
    auto sp_mongo_db = MongoDBHandlerSingleton::get_instance();
    TopOfBookHandler topOfBookHandler(sp_mongo_db, tob_websocket_server_);
    mobile_book_handler::LastBarterHandler lastBarterHandler(sp_mongo_db, lt_websocket_server_, topOfBookHandler, lastBarterCache, topOfBookCache);

    mobile_book::LastBarter last_barter;
    last_barter.set_id(id);
    last_barter.set_px(px);
    last_barter.set_qty(qty);
    last_barter.set_premium(premium);
    last_barter.set_exch_time(exch_time);
    last_barter.set_arrival_time(arrival_time);
    last_barter.mutable_symbol_n_exch_id()->set_symbol(symbol);
    last_barter.mutable_symbol_n_exch_id()->set_exch_id(exch_id);
    last_barter.mutable_market_barter_volume()->set_id(market_barter_volume_id);
    last_barter.mutable_market_barter_volume()->set_participation_period_last_barter_qty_sum(participation_period_last_barter_qty_sum);
    last_barter.mutable_market_barter_volume()->set_applicable_period_seconds(applicable_period_seconds);

    lastBarterHandler.handle_last_barter_update(last_barter);
    std::cout << "create_or_update_last_barter_n_tob end" << std::endl;
}

extern "C" void websocket_cleanup() {
    tob_websocket_server_.shutdown();
    m_top_of_book_websocket_thread_.join();
    lt_websocket_server_.shutdown();
    m_last_barter_websocket_thread_.join();
    md_websocket_server_.shutdown();
    m_market_depth_websocket_thread_.join();
}