#pragma once


#include "mobile_book_publisher.h"


class MobileBookConsumer {
public:
    explicit MobileBookConsumer(const std::string& kr_yaml_config_file) :
    k_mr_yaml_config_file_(kr_yaml_config_file), m_mobile_book_publisher_(k_mr_yaml_config_file_) {}

    void process_market_depth(const MarketDepthQueueElement &md) {
        LOG_INFO_IMPL(GetCppAppLogger(), "inside: {}: {}", __func__, md.symbol_);
        m_mobile_book_publisher_.process_market_depth(md);
        PyMarketDepthQueueElement md_market_depth{md.symbol_.c_str(), md.exch_time_.c_str(),
            md.arrival_time_.c_str(), md.side_, md.px_, md.is_px_set_, md.qty_, md.is_qty_set_,
            md.position_, md.market_maker_.c_str(), md.is_market_maker_set_, md.is_smart_depth_,
            md.is_is_smart_depth_set_, md.cumulative_notional_, md.is_cumulative_notional_set_, md.cumulative_qty_,
            md.is_cumulative_qty_set_, md.cumulative_avg_px_, md.is_cumulative_avg_px_set_};
        LOG_INFO_IMPL(GetCppAppLogger(), "process_market_depth cache: {}", md.symbol_);
        mkt_depth_fp(&md_market_depth);
        LOG_INFO_IMPL(GetCppAppLogger(), "exit: {}: {}", __func__, md.symbol_);
    }

    void process_last_barter(const LastBarterQueueElement &e) {
        m_mobile_book_publisher_.process_last_barter(e);
        PyLastBarterQueueElement last_barter{{e.symbol_n_exch_id_.symbol_.c_str(),
            e.symbol_n_exch_id_.exch_id_.c_str()}, e.exch_time_.c_str(), e.arrival_time_.c_str(),
            e.px_, e.qty_, e.premium_, e.is_premium_set_,
            {e.market_barter_volume_.id_.c_str(),
                e.market_barter_volume_.participation_period_last_barter_qty_sum_,
                e.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_,
                e.market_barter_volume_.applicable_period_seconds_,
                e.market_barter_volume_.is_applicable_period_seconds_set_},
            e.is_market_barter_volume_set_};
        last_barter_fp(&last_barter);
    }

    void go() {
		int market_depth_index = 0;
		int last_barter_index = 0;

		while (market_depth_index < m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history_size() or
			last_barter_index < m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history_size()) {
			if (market_depth_index < m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history_size() and
				last_barter_index >= m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history_size()) {

				char side;
				if (m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).side() ==
					mobile_book::TickType::BID) {
					side = 'B';
					} else {
						side = 'A';
					}

				MarketDepthQueueElement mkt_depth;
				mkt_depth.id_ = m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).id();
				mkt_depth.symbol_ = m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(
					market_depth_index).symbol_n_exch_id().symbol();
				mkt_depth.exch_time_ = m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(
					market_depth_index).exch_time();
				mkt_depth.arrival_time_ = m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(
					market_depth_index).arrival_time();
				mkt_depth.side_ = side;
				if (m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).has_px()) {
					mkt_depth.px_ = m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).px();
					mkt_depth.is_px_set_ = true;
				} else {
					mkt_depth.px_ = 0;
					mkt_depth.is_px_set_ = false;
				}

				if (m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).has_qty()) {
					mkt_depth.qty_ = m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).qty();
					mkt_depth.is_qty_set_ = true;
				} else {
					mkt_depth.qty_ = 0;
					mkt_depth.is_qty_set_ = false;
				}
				mkt_depth.position_ = m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).position();
				mkt_depth.market_maker_ = "";
				mkt_depth.is_market_maker_set_ = false;
				mkt_depth.is_smart_depth_ = false;
				mkt_depth.is_is_smart_depth_set_ = false;
				mkt_depth.cumulative_notional_ = 0.0;
				mkt_depth.is_cumulative_notional_set_ = false;
				mkt_depth.cumulative_qty_ = 0;
				mkt_depth.is_cumulative_qty_set_ = false;
				mkt_depth.cumulative_avg_px_ = 0;
				mkt_depth.is_cumulative_avg_px_set_ = false;

				process_market_depth(mkt_depth);
				++market_depth_index;

			} else {

				// Replay last barter

				LastBarterQueueElement last_barter;
				last_barter.id_ = m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(last_barter_index).id();
				last_barter.symbol_n_exch_id_.symbol_ = m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
					last_barter_index).symbol_n_exch_id().symbol();
				last_barter.symbol_n_exch_id_.exch_id_ = m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
					last_barter_index).symbol_n_exch_id().exch_id();
				last_barter.exch_time_ = m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(last_barter_index).exch_time();
				last_barter.arrival_time_ = m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(last_barter_index).arrival_time();
				last_barter.px_ = m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(last_barter_index).px();
				last_barter.qty_ = m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(last_barter_index).qty();
				if (m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(last_barter_index).has_premium()) {
					last_barter.premium_ = m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(last_barter_index).premium();
					last_barter.is_premium_set_ = true;
				} else {
					last_barter.premium_ = 0;
					last_barter.is_premium_set_ = false;
				}

				if (m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(last_barter_index).has_market_barter_volume()) {
					last_barter.market_barter_volume_.id_ = m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).market_barter_volume().id();
					if (m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).market_barter_volume().has_participation_period_last_barter_qty_sum()) {
						last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_ =
							m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
								last_barter_index).market_barter_volume().participation_period_last_barter_qty_sum();
						last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = true;
					} else {
						last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_ = 0;
						last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = false;
					}

					if (m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).market_barter_volume().has_applicable_period_seconds()) {
						last_barter.market_barter_volume_.applicable_period_seconds_ =
							m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
								last_barter_index).market_barter_volume().applicable_period_seconds();
						last_barter.market_barter_volume_.is_applicable_period_seconds_set_ = true;
					} else {
						last_barter.market_barter_volume_.applicable_period_seconds_ = 0;
						last_barter.market_barter_volume_.is_applicable_period_seconds_set_ = false;
					}
					last_barter.is_market_barter_volume_set_ = true;
				} else {
					last_barter.market_barter_volume_.id_ = "";
					last_barter.market_barter_volume_.applicable_period_seconds_ = 0;
					last_barter.market_barter_volume_.is_applicable_period_seconds_set_ = false;
					last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_ = 0;
					last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = false;
					last_barter.is_market_barter_volume_set_ = false;
				}
				process_last_barter(last_barter);

				++last_barter_index;
			}
		}
		LOG_INFO_IMPL(GetCppAppLogger(), "exit: {}", __func__);
	}
protected:
    const std::string& k_mr_yaml_config_file_;
    MobileBookPublisher m_mobile_book_publisher_;
};
