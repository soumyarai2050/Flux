#pragma once

#include <Python.h>
#include <mobile_book_service.pb.h>
#include "quill/Quill.h"

#include "market_depth_handler.h"
#include "last_barter_handler.h"
#include "mongo_db_singleton.h"
#include "cpp_app_shared_resource.h"

extern MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook> top_of_book_websocket_server;
extern MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> last_barter_websocket_server;
extern MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> market_depth_websocket_server;
extern std::thread top_of_book_ws_thread;
extern std::thread last_barter_ws_thread;
extern std::thread market_depth_ws_thread;


extern "C" void lock_mutex(PyObject* p_mutex_ptr);


extern "C" void unlock_mutex(PyObject* p_mutex_ptr);

extern "C" void initialize_database(const char* db_uri, const char* db_name, PyObject* port_dict);

extern "C" void create_or_update_md_n_tob(const int32_t id, const char* symbol,
                                          const char* exch_time, const char* arrival_time, const int side,
                                          const int32_t position, const float px = 0, const int64_t qty = 0,
                                          const char* market_maker = "", const bool is_smart_depth = false,
                                          const float cumulative_notional = 0, const int64_t cumulative_qty = 0,
                                          const float cumulative_avg_px = 0);



extern "C" void create_or_update_last_barter_n_tob(const int32_t id, const char* symbol, const char* exch_id, const char* exch_time,
                                                 const char* arrival_time, const float px, const int64_t qty, const float premium = 0,
                                                 const char* market_barter_volume_id = "", const int64_t participation_period_last_barter_qty_sum = 0,
                                                 const int32_t applicable_period_seconds = 0);

extern "C" void websocket_cleanup();