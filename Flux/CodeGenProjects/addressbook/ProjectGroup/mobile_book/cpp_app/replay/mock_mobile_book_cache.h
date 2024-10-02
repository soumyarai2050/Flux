#pragma once

#include "mobile_book_consumer.h"


extern "C" void initialize_database(const char* db_uri, const char* db_name);

extern "C" void create_or_update_md_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
    [[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const char side, const int32_t position,
    const double px, const int64_t qty, const char *market_maker, const bool is_smart_depth,
    const double cumulative_notional, const int64_t cumulative_qty, const double cumulative_avg_px);



extern "C" void create_or_update_last_barter_n_tob([[maybe_unused]] const int32_t id, const char *symbol,
    const char *exch_id, [[maybe_unused]] const char *exch_time, [[maybe_unused]] const char *arrival_time, const double px,
    const int64_t qty, const double premium, const char *market_barter_volume_id,
    const int64_t participation_period_last_barter_qty_sum, const int32_t applicable_period_seconds);


