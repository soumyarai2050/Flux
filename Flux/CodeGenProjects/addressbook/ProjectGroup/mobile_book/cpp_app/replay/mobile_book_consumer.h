#pragma once


#include "mobile_book_publisher.h"


class MobileBookConsumer {
public:
    explicit MobileBookConsumer(Config& r_config) :
    mr_config_(r_config), m_mobile_book_publisher_(mr_config_) {}

    void process_market_depth(MarketDepth &md) {
        m_mobile_book_publisher_.process_market_depth(md);
    }

    void process_last_barter(LastBarter &e) {
        m_mobile_book_publisher_.process_last_barter(e);
    }

	void cleanup() {
	    m_mobile_book_publisher_.cleanup();
    }

	void process_market_depth(std::string &md_str) {

    	MarketDepth market_depth;
    	MobileBookJsonToObject::json_to_object(md_str, market_depth);
	    auto time  = FluxCppCore::get_local_time_microseconds<int64_t>();

    	market_depth.exch_time_ = time;
    	market_depth.arrival_time_ = time;
    	process_market_depth(market_depth);
    }

	void process_last_barter(std::string &lt_str) {

    	LastBarter last_barter;
		MobileBookJsonToObject::json_to_object(lt_str, last_barter);
	    auto time  = FluxCppCore::get_local_time_microseconds<int64_t>();
    	last_barter.exch_time_ = time;
    	last_barter.arrival_time_ = time;
    	process_last_barter(last_barter);
    }

	void init_shm() {
	    m_mobile_book_publisher_.init_shared_memory();
    }


    void go() {
    	size_t market_depth_index = 0;
		size_t last_barter_index = 0;

		while (market_depth_index < m_mobile_book_publisher_.m_raw_market_depth_history_list_.raw_market_depth_history_.size() or
			last_barter_index < m_mobile_book_publisher_.m_raw_last_barter_history_list_.raw_last_barter_history_.size()) {
			if (market_depth_index < m_mobile_book_publisher_.m_raw_market_depth_history_list_.raw_market_depth_history_.size() and
				last_barter_index >= m_mobile_book_publisher_.m_raw_last_barter_history_list_.raw_last_barter_history_.size()) {

				auto md =
					m_mobile_book_publisher_.m_raw_market_depth_history_list_.raw_market_depth_history_.at(
						market_depth_index);
				MarketDepth market_depth{
					.id_ = md.id_,
					.symbol_ = md.symbol_n_exch_id_.symbol_,
					.exch_time_ = md.exch_time_,
					.arrival_time_ = md.arrival_time_,
					.side_ = md.side_,
					.px_ = md.px_,
					.is_px_set_ = true,
                    .qty_ = md.qty_,
					.is_qty_set_ = true,
                    .position_ = md.position_,
					.is_market_maker_set_ = false,
					.is_is_smart_depth_set_ = false,
					.is_cumulative_notional_set_ = false,
					.is_cumulative_qty_set_ = false,
					.is_cumulative_avg_px_set_ = false
				};

				process_market_depth(market_depth);
				++market_depth_index;

			} else {

				// Replay last barter

				auto lt = m_mobile_book_publisher_.m_raw_last_barter_history_list_.raw_last_barter_history_.at(last_barter_index);
				LastBarter last_barter{
					.id_ = lt.id_,
					.symbol_n_exch_id_ = lt.symbol_n_exch_id_,
                    .exch_time_ = lt.exch_time_,
                    .arrival_time_ = lt.arrival_time_,
                    .px_ = lt.px_,
					.qty_ = lt.qty_,
					.premium_ = lt.premium_,
					.is_premium_set_ = lt.is_premium_set_,
					.market_barter_volume_ = lt.market_barter_volume_,
					.is_market_barter_volume_set_ = lt.is_market_barter_volume_set_
				};

				process_last_barter(last_barter);

				++last_barter_index;
			}
		}
		LOG_INFO_IMPL(GetCppAppLogger(), "exit: {}", __func__);
	}
protected:
    Config& mr_config_;
    MobileBookPublisher m_mobile_book_publisher_;
};
