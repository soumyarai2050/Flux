#include "mock_mobile_book_cache.h"

MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook> top_of_book_websocket_server(
    mobile_book_handler::top_of_book_obj, host, tob_ws_port, mobile_book_handler::TIME_OUT_CONNECTION);
MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> last_barter_websocket_server(
    mobile_book_handler::last_barter_obj, host, lt_ws_port, mobile_book_handler::TIME_OUT_CONNECTION);
MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> market_depth_websocket_server(
    mobile_book_handler::market_depth_obj, host, md_ws_port, TIME_OUT_CONNECTION);
std::thread top_of_book_ws_thread{[](){top_of_book_websocket_server.run();}};
std::thread last_barter_ws_thread{[](){last_barter_websocket_server.run();}};
std::thread market_depth_ws_thread{[](){market_depth_websocket_server.run();}};

void lock_mutex(PyObject *p_mutex_ptr) {
    assert(p_mutex_ptr != nullptr && "mutex pointer never be null");
    void* mutex_void_ptr = PyLong_AsVoidPtr(p_mutex_ptr);

    assert(mutex_void_ptr != nullptr && "Failed to convert into void ptr");

    auto std_mutex_ptr = static_cast<std::mutex*>(mutex_void_ptr);
    std_mutex_ptr->lock();
}

void unlock_mutex(PyObject *p_mutex_ptr) {
    assert(p_mutex_ptr != nullptr);

    void* mutex_void_ptr = PyLong_AsVoidPtr(p_mutex_ptr);
    assert(mutex_void_ptr != nullptr);

    // Cast the pointer to std::mutex* type
    auto std_mutex_ptr = static_cast<std::mutex*>(mutex_void_ptr);
    std_mutex_ptr->unlock();
}

void initialize_database(const char *db_uri, const char *db_name, PyObject *port_dict) {

    LOG_ERROR_IMPL(GetLogger(), "inside: {}", __func__);	
    MongoDBHandlerSingleton::get_instance(db_uri, db_name);

    // Acquire the GIL
    PyGILState_STATE gstate = PyGILState_Ensure();
    // Update the port dictionary
    PyDict_SetItemString(port_dict, top_of_book_port_key.c_str(), PyLong_FromLong(tob_ws_port));
    PyDict_SetItemString(port_dict, market_depth_port_key.c_str(), PyLong_FromLong(md_ws_port));
    PyDict_SetItemString(port_dict, last_barter_port_key.c_str(), PyLong_FromLong(lt_ws_port));

    // Release the GIL
    PyGILState_Release(gstate);
}

void create_or_update_md_n_tob(const int32_t id, const char *symbol, [[maybe_unused]] const char *exch_time,
    [[maybe_unused]] const char *arrival_time, const int side, const int32_t position, const float px, const int64_t qty,
    const char *market_maker, const bool is_smart_depth, const float cumulative_notional,
    const int64_t cumulative_qty, const float cumulative_avg_px) {

    mobile_book::TickType k_side;
    if (side == 1) {
        k_side = mobile_book::TickType::BID;
    } else if (side == 2) {
        k_side = mobile_book::TickType::ASK;
    }


    auto sp_mongo_db = MongoDBHandlerSingleton::get_instance();
    static TopOfBookHandler topOfBookHandler(sp_mongo_db, top_of_book_websocket_server);
    static MarketDepthHandler market_depth_handler(sp_mongo_db, market_depth_websocket_server, topOfBookHandler);


    mobile_book::MarketDepth market_depth;
    auto date_time = FluxCppCore::get_utc_time_microseconds();
    market_depth.set_id(id);
    market_depth.set_symbol(symbol);
    market_depth.set_exch_time(date_time);
    market_depth.set_arrival_time(date_time);
    market_depth.set_side(k_side);
    market_depth.set_px(px);
    market_depth.set_qty(qty);
    market_depth.set_position(position);
    market_depth.set_market_maker(market_maker);
    market_depth.set_is_smart_depth(is_smart_depth);
    market_depth.set_cumulative_notional(cumulative_notional);
    market_depth.set_cumulative_qty(cumulative_qty);
    market_depth.set_cumulative_avg_px(cumulative_avg_px);

    market_depth_handler.handle_md_update(market_depth);
}

void create_or_update_last_barter_n_tob(const int32_t id, const char *symbol, const char *exch_id,
    [[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const float px, const int64_t qty, const float premium,
    const char *market_barter_volume_id, const int64_t participation_period_last_barter_qty_sum,
    const int32_t applicable_period_seconds) {

    auto sp_mongo_db = MongoDBHandlerSingleton::get_instance();
    static TopOfBookHandler topOfBookHandler(sp_mongo_db, top_of_book_websocket_server);
    static mobile_book_handler::LastBarterHandler lastBarterHandler(sp_mongo_db, last_barter_websocket_server,
        topOfBookHandler);

    mobile_book::LastBarter last_barter;
    last_barter.set_id(id);
    last_barter.set_px(px);
    last_barter.set_qty(qty);
    last_barter.set_premium(premium);
    // last_barter.set_exch_time(FluxCppCore::get_utc_time_microseconds());
    // last_barter.set_arrival_time(FluxCppCore::get_utc_time_microseconds());
    last_barter.mutable_symbol_n_exch_id()->set_symbol(symbol);
    last_barter.mutable_symbol_n_exch_id()->set_exch_id(exch_id);
    last_barter.mutable_market_barter_volume()->set_id(market_barter_volume_id);
    last_barter.mutable_market_barter_volume()->set_participation_period_last_barter_qty_sum(participation_period_last_barter_qty_sum);
    last_barter.mutable_market_barter_volume()->set_applicable_period_seconds(applicable_period_seconds);

    lastBarterHandler.handle_last_barter_update(last_barter);
}

void add_symbols_to_the_cache_container() {
    std::vector<std::string> symbols;
    FluxCppCore::get_barter_symbols_from_config(symbols);
    int8_t market_depth_levels = FluxCppCore::get_market_depth_levels_from_config();
    for (const auto& symbol : symbols) {
        FluxCppCore::AddOrGetContainerObj::add_container_obj_for_symbol(symbol);
        for (int8_t i = 0; i < market_depth_levels; ++i) {
            mobile_book_handler::market_cache::MarketDepthCache::create_bid_market_depth_cache(symbol, i);
            mobile_book_handler::market_cache::MarketDepthCache::create_ask_market_depth_cache(symbol, i);
        }
        mobile_book_handler::market_cache::TopOfBookCache::create_top_of_book_cache(symbol);
        mobile_book_handler::market_cache::LastBarterCache::create_last_barter_cache(symbol);
    }
}


void websocket_cleanup() {
    top_of_book_websocket_server.shutdown();
    top_of_book_ws_thread.join();
    last_barter_websocket_server.shutdown();
    last_barter_ws_thread.join();
    market_depth_websocket_server.shutdown();
    market_depth_ws_thread.join();
}
