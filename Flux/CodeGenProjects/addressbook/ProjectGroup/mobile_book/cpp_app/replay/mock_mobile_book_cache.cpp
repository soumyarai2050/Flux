#ifdef TEST

#include "mock_mobile_book_cache.h"
#include "mobile_book_interface.h"
#include "mobile_book_service_shared_data_structure.h"


/**
 * @brief Creates or updates the last barter and top-of-book information.
 *
 * This function creates a LastBarterQueueElement with the provided barter information
 * and processes it using the mobile_book_consumer.
 *
 * @param id [maybe_unused] The barter identifier.
 * @param symbol The bartering symbol.
 * @param exch_id The exchange identifier.
 * @param exch_time [maybe_unused] The exchange timestamp of the barter.
 * @param arrival_time [maybe_unused] The arrival timestamp of the barter data.
 * @param px The price of the barter.
 * @param qty The quantity of the barter.
 * @param premium The premium associated with the barter.
 * @param market_barter_volume_id The market barter volume identifier.
 * @param participation_period_last_barter_qty_sum The sum of quantities for the last barters in the participation period.
 * @param applicable_period_seconds The applicable period in seconds.
 *
 * @return This function does not return a value.
 */

extern "C" void create_or_update_last_barter_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
	const char *exch_id, [[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const double px,
	const int64_t qty, const double premium, const char *market_barter_volume_id,
	const int64_t participation_period_last_barter_qty_sum, const int32_t applicable_period_seconds) {

	auto int_ts = FluxCppCore::get_local_time_microseconds();
	LastBarterQueueElement last_barter{id, {{}, {}}, {}, {},
		px, qty, premium,
		true, {
			{}, participation_period_last_barter_qty_sum,
			true, applicable_period_seconds, true},
		true};

	FluxCppCore::StringUtil::setString(last_barter.symbol_n_exch_id_.symbol_, symbol,
		sizeof(last_barter.symbol_n_exch_id_.symbol_));
	FluxCppCore::StringUtil::setString(last_barter.symbol_n_exch_id_.exch_id_, exch_id,
		sizeof(last_barter.symbol_n_exch_id_.exch_id_));
	FluxCppCore::StringUtil::setString(last_barter.exch_time_, int_ts.c_str(), sizeof(last_barter.exch_time_));
	FluxCppCore::StringUtil::setString(last_barter.arrival_time_, int_ts.c_str(), sizeof(last_barter.arrival_time_));
	FluxCppCore::StringUtil::setString(last_barter.market_barter_volume_.id_, market_barter_volume_id,
		sizeof(last_barter.market_barter_volume_.id_));

	mobile_book_consumer->process_last_barter(last_barter);

}


extern "C" void create_or_update_md_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
	[[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const char side, const int32_t position,
	const double px, const int64_t qty, const char *market_maker, const bool is_smart_depth,
	const double cumulative_notional, const int64_t cumulative_qty, const double cumulative_avg_px) {

	auto int_ts = FluxCppCore::get_local_time_microseconds();

	MarketDepthQueueElement mkt_depth{id, {}, {}, {}, side, px,
		true, qty, true, position, {}, true,
		is_smart_depth, true, cumulative_notional, true,
		cumulative_qty, true, cumulative_avg_px, true};

	FluxCppCore::StringUtil::setString(mkt_depth.symbol_, symbol, sizeof(mkt_depth.symbol_));
	FluxCppCore::StringUtil::setString(mkt_depth.exch_time_, int_ts.c_str(), sizeof(mkt_depth.exch_time_));
	FluxCppCore::StringUtil::setString(mkt_depth.arrival_time_, int_ts.c_str(), sizeof(mkt_depth.arrival_time_));
	FluxCppCore::StringUtil::setString(mkt_depth.market_maker_, market_maker, sizeof(mkt_depth.market_maker_));

	if (mobile_book_consumer) {
		mobile_book_consumer->process_market_depth(mkt_depth);
	} else {
		LOG_ERROR_IMPL(GetCppAppLogger(), "mobile_book_consumer is null");
	}
}

#endif