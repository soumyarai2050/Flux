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

void websocket_cleanup() {
    top_of_book_websocket_server.shutdown();
    top_of_book_ws_thread.join();
    last_barter_websocket_server.shutdown();
    last_barter_ws_thread.join();
    market_depth_websocket_server.shutdown();
    market_depth_ws_thread.join();
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

extern "C" void create_or_update_last_barter_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
	const char *exch_id, [[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const double px,
	const int64_t qty, const double premium, const char *market_barter_volume_id,
	const int64_t participation_period_last_barter_qty_sum, const int32_t applicable_period_seconds) {

	auto int_ts = FluxCppCore::get_utc_time_microseconds();
	std::string time_str;
	FluxCppCore::format_time(int_ts, time_str);
	PyLastBarter last_barter{{symbol, exch_id}, time_str.c_str(), time_str.c_str(),
		px, qty, premium, {market_barter_volume_id, participation_period_last_barter_qty_sum, applicable_period_seconds}};

	auto sp_mongo_db = MongoDBHandlerSingleton::get_instance();
	static MobileBookConsumer mobile_book_consumer(sp_mongo_db, top_of_book_websocket_server,
	last_barter_websocket_server, market_depth_websocket_server);
	mobile_book_consumer.process_last_barter(last_barter);
}


extern "C" void create_or_update_md_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
	[[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const char side, const int32_t position,
	const double px, const int64_t qty, const char *market_maker, const bool is_smart_depth,
	const double cumulative_notional, const int64_t cumulative_qty, const double cumulative_avg_px) {

	auto int_ts = FluxCppCore::get_utc_time_microseconds();
	std::string time_str;
	FluxCppCore::format_time(int_ts, time_str);

	PyMktDepth mkt_depth{symbol, time_str.c_str(), time_str.c_str(), side, position, px,
		qty, market_maker, is_smart_depth, cumulative_notional, cumulative_qty, cumulative_avg_px};
	auto sp_mongo_db = MongoDBHandlerSingleton::get_instance();

	static MobileBookConsumer mobile_book_consumer(sp_mongo_db, top_of_book_websocket_server,
	last_barter_websocket_server, market_depth_websocket_server);
	mobile_book_consumer.process_market_depth(mkt_depth);

}

