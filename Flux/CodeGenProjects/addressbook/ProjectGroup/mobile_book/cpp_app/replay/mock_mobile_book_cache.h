#pragma once

#include <Python.h>
#include "mobile_book_consumer.h"
#include "mongo_db_singleton.h"

extern MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook> top_of_book_websocket_server;
extern MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> last_barter_websocket_server;
extern MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> market_depth_websocket_server;
extern std::thread top_of_book_ws_thread;
extern std::thread last_barter_ws_thread;
extern std::thread market_depth_ws_thread;

extern "C" void websocket_cleanup();

extern "C" void initialize_database(const char* db_uri, const char* db_name, PyObject* port_dict);

extern "C" void create_or_update_md_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
    [[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const char side, const int32_t position,
    const double px, const int64_t qty, const char *market_maker, const bool is_smart_depth,
    const double cumulative_notional, const int64_t cumulative_qty, const double cumulative_avg_px);



extern "C" void create_or_update_last_barter_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
    const char *exch_id, [[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const double px,
    const int64_t qty, const double premium, const char *market_barter_volume_id,
    const int64_t participation_period_last_barter_qty_sum, const int32_t applicable_period_seconds);


