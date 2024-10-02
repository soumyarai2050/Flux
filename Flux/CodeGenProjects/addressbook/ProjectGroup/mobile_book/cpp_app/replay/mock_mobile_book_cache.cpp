#include "mock_mobile_book_cache.h"
#include "mobile_book_interface.h"


extern "C" void create_or_update_last_barter_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
	const char *exch_id, [[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const double px,
	const int64_t qty, const double premium, const char *market_barter_volume_id,
	const int64_t participation_period_last_barter_qty_sum, const int32_t applicable_period_seconds) {

	auto int_ts = FluxCppCore::get_utc_time_microseconds();
	std::string time_str;
	FluxCppCore::format_time(int_ts, time_str);
	LastBarter last_barter{id, {symbol, exch_id}, time_str, time_str,
		px, qty, premium,
		true, {
			market_barter_volume_id, participation_period_last_barter_qty_sum,
			true, applicable_period_seconds, true},
		true};
	mobile_book_consumer->process_last_barter(last_barter);

}


extern "C" void create_or_update_md_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
	[[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const char side, const int32_t position,
	const double px, const int64_t qty, const char *market_maker, const bool is_smart_depth,
	const double cumulative_notional, const int64_t cumulative_qty, const double cumulative_avg_px) {

	auto int_ts = FluxCppCore::get_utc_time_microseconds();
	std::string time_str;
	FluxCppCore::format_time(int_ts, time_str);

	MarketDepth mkt_depth{id, symbol, time_str, time_str, side, px,
		true, qty, true, position, market_maker, true,
		is_smart_depth, true, cumulative_notional, true,
		cumulative_qty, true, cumulative_avg_px, true};

	if (mobile_book_consumer) {
		mobile_book_consumer->process_market_depth(mkt_depth);
	} else {
		LOG_ERROR(GetLogger(), "mobile_book_consumer is null");
	}
}

