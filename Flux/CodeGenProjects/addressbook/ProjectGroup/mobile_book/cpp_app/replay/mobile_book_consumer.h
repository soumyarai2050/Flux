#pragma once


#include "mobile_book_publisher.h"


class MobileBookConsumer {
public:
    explicit MobileBookConsumer(Config& r_config, MobileBookPublisher& mobile_book_publisher) :
    mr_config_(r_config), m_mobile_book_publisher_(mobile_book_publisher) {}

    void process_market_depth(const MarketDepthQueueElement &md) {
        m_mobile_book_publisher_.process_market_depth(md);
    }

    void process_last_barter(const LastBarterQueueElement &e) {
        m_mobile_book_publisher_.process_last_barter(e);
    }

	void cleanup() {
	    m_mobile_book_publisher_.cleanup();
    }

	void process_market_depth(const std::string &md_str) {

    	MarketDepth market_depth;
    	MobileBookJsonToObject::json_to_object(md_str, market_depth);
	    auto time  = FluxCppCore::get_local_time_microseconds<int64_t>();

    	market_depth.exch_time_ = time;
    	market_depth.arrival_time_ = time;
    	MarketDepthQueueElement market_depth_queue_element{
			.id_ = market_depth.id_,
            .exch_time_ = market_depth.exch_time_,
            .arrival_time_ = market_depth.arrival_time_,
    		.side_ = market_depth.side_[0],
    		.px_ = market_depth.px_,
    		.is_px_set_ = market_depth.is_px_set_,
    		.qty_ = market_depth.qty_,
    		.is_qty_set_ = market_depth.is_qty_set_,
    		.position_ = market_depth.position_,
    		.is_smart_depth_ = market_depth.is_smart_depth_,
    		.is_is_smart_depth_set_ = market_depth.is_is_smart_depth_set_,
    		.cumulative_notional_ = market_depth.cumulative_notional_,
    		.is_cumulative_notional_set_ = market_depth.is_cumulative_notional_set_,
    		.cumulative_qty_ = market_depth.cumulative_qty_,
    		.is_cumulative_qty_set_ = market_depth.is_cumulative_qty_set_,
    		.cumulative_avg_px_ = market_depth.cumulative_avg_px_,
    		.is_cumulative_avg_px_set_ = market_depth.is_cumulative_avg_px_set_
    	};

    	FluxCppCore::StringUtil::setString(market_depth_queue_element.symbol_, market_depth.symbol_);
    	if (market_depth.is_market_maker_set_) {
    		FluxCppCore::StringUtil::setString(market_depth_queue_element.market_maker_,
                market_depth.market_maker_);
            market_depth_queue_element.is_market_maker_set_ = true;
    	}

    	process_market_depth(market_depth_queue_element);
    }

	void process_last_barter(const std::string &lt_str) {

    	LastBarter last_barter;
		MobileBookJsonToObject::json_to_object(lt_str, last_barter);
	    auto time  = FluxCppCore::get_local_time_microseconds<int64_t>();
    	last_barter.exch_time_ = time;
    	last_barter.arrival_time_ = time;
    	LastBarterQueueElement last_barter_queue_element{
			.id_ = last_barter.id_,
    		.exch_time_ = last_barter.exch_time_,
    		.arrival_time_ = last_barter.arrival_time_,
            .px_ = last_barter.px_,
            .qty_ = last_barter.qty_,
    		.premium_ = last_barter.premium_,
    		.is_premium_set_ = last_barter.is_premium_set_,
    	};

    	FluxCppCore::StringUtil::setString(last_barter_queue_element.symbol_n_exch_id_.symbol_,
    		last_barter.symbol_n_exch_id_.symbol_);
    	FluxCppCore::StringUtil::setString(last_barter_queue_element.symbol_n_exch_id_.exch_id_,
            last_barter.symbol_n_exch_id_.exch_id_);

    	if (last_barter.is_market_barter_volume_set_) {
    		FluxCppCore::StringUtil::setString(last_barter_queue_element.market_barter_volume_.id_, last_barter.market_barter_volume_.id_);
    		if (last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_) {
    			last_barter_queue_element.market_barter_volume_.participation_period_last_barter_qty_sum_ =
    				last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_;
    			last_barter_queue_element.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = true;
    		}
    		if (last_barter.market_barter_volume_.is_applicable_period_seconds_set_) {
    			last_barter_queue_element.market_barter_volume_.applicable_period_seconds_ =
                    last_barter.market_barter_volume_.applicable_period_seconds_;
                last_barter_queue_element.market_barter_volume_.is_applicable_period_seconds_set_ = true;
    		}
    		last_barter_queue_element.is_market_barter_volume_set_ = true;
    	}
    	process_last_barter(last_barter_queue_element);
    }

	void init_shm() {
	    m_mobile_book_publisher_.init_shared_memory();
    }


    void go()  {
    	size_t market_depth_index = 0;
		size_t last_barter_index = 0;

		while (market_depth_index < m_mobile_book_publisher_.m_raw_market_depth_history_list_.raw_market_depth_history_.size() or
			last_barter_index < m_mobile_book_publisher_.m_raw_last_barter_history_list_.raw_last_barter_history_.size()) {
			if (market_depth_index < m_mobile_book_publisher_.m_raw_market_depth_history_list_.raw_market_depth_history_.size() and
				last_barter_index >= m_mobile_book_publisher_.m_raw_last_barter_history_list_.raw_last_barter_history_.size()) {

				auto md =
					m_mobile_book_publisher_.m_raw_market_depth_history_list_.raw_market_depth_history_.at(
						market_depth_index);
				MarketDepthQueueElement market_depth{
					.id_ = md.id_,
					.exch_time_ = md.exch_time_,
					.arrival_time_ = md.arrival_time_,
					.side_ = md.side_[0],
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

				FluxCppCore::StringUtil::setString(market_depth.symbol_, md.symbol_n_exch_id_.symbol_);

				m_mobile_book_publisher_.process_market_depth(market_depth);
				++market_depth_index;

			} else {

				// Replay last barter

				auto lt = m_mobile_book_publisher_.m_raw_last_barter_history_list_.raw_last_barter_history_.at(last_barter_index);
				LastBarterQueueElement last_barter{
					.id_ = lt.id_,
                    .exch_time_ = lt.exch_time_,
                    .arrival_time_ = lt.arrival_time_,
                    .px_ = lt.px_,
					.qty_ = lt.qty_,
					.premium_ = lt.premium_,
					.is_premium_set_ = lt.is_premium_set_,
					.is_market_barter_volume_set_ = lt.is_market_barter_volume_set_
				};

				FluxCppCore::StringUtil::setString(last_barter.symbol_n_exch_id_.symbol_, lt.symbol_n_exch_id_.symbol_);
				FluxCppCore::StringUtil::setString(last_barter.symbol_n_exch_id_.exch_id_, lt.symbol_n_exch_id_.exch_id_);

				if (lt.is_market_barter_volume_set_) {
					FluxCppCore::StringUtil::setString(last_barter.market_barter_volume_.id_, lt.market_barter_volume_.id_);
                    if (lt.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_) {
                        last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_ =
                            lt.market_barter_volume_.participation_period_last_barter_qty_sum_;
                        last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = true;
                    }

					if (lt.market_barter_volume_.is_applicable_period_seconds_set_) {
                        last_barter.market_barter_volume_.applicable_period_seconds_ = lt.market_barter_volume_.applicable_period_seconds_;
                        last_barter.market_barter_volume_.is_applicable_period_seconds_set_ = true;
                    }
				}
				m_mobile_book_publisher_.process_last_barter(last_barter);

				++last_barter_index;
			}
		}
		LOG_INFO_IMPL(GetCppAppLogger(), "exit: {}", __func__);
	}
protected:
    Config& mr_config_;
    MobileBookPublisher& m_mobile_book_publisher_;
};
