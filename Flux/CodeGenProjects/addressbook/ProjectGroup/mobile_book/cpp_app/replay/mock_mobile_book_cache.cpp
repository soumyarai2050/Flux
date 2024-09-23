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



extern "C" void create_or_update_last_barter_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
	const char *exch_id, [[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const double px,
	const int64_t qty, const double premium, const char *market_barter_volume_id,
	const int64_t participation_period_last_barter_qty_sum, const int32_t applicable_period_seconds) {

	auto int_ts = FluxCppCore::get_utc_time_microseconds();
	std::string time_str;
	FluxCppCore::format_time(int_ts, time_str);
	PyLastBarter last_barter{{symbol, exch_id}, time_str.c_str(), time_str.c_str(),
		px, qty, premium, {market_barter_volume_id, participation_period_last_barter_qty_sum, applicable_period_seconds}};

    const char* app_name = getenv("simulate_config_yaml_file");
    if (!app_name) {
        throw std::runtime_error("export env variable {app_name}");
    }
    if (access(app_name, F_OK) != 0) {
        throw std::runtime_error(std::format("{} not accessable", app_name));
    }
    YAML::Node config_file = YAML::LoadFile(app_name);
    auto db = MongoDBHandlerSingleton::get_instance();
	static MobileBookConsumer mobile_book_consumer(config_file, db, top_of_book_websocket_server,
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

	const char* app_name = getenv("simulate_config_yaml_file");
    if (!app_name) {
        throw std::runtime_error("export env variable {app_name}");
    }
    if (access(app_name, F_OK) != 0) {
        throw std::runtime_error(std::format("{} not accessable", app_name));
    }

    YAML::Node config_file = YAML::LoadFile(app_name);
    auto db = MongoDBHandlerSingleton::get_instance();
	static MobileBookConsumer mobile_book_consumer(config_file, db, top_of_book_websocket_server,
	last_barter_websocket_server, market_depth_websocket_server);

	mobile_book_consumer.process_market_depth(mkt_depth);

}

