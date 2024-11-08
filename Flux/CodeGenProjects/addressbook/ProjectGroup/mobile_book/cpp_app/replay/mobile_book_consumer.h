#pragma once


#include "mobile_book_publisher.h"


class MobileBookConsumer {
public:
    explicit MobileBookConsumer(Config& r_config) :
    mr_config_(r_config), m_mobile_book_publisher_(mr_config_) {}

    void process_market_depth(const MarketDepthQueueElement &md) {
        m_mobile_book_publisher_.process_market_depth(md);
    }

    void process_last_barter(const LastBarterQueueElement &e) {
        m_mobile_book_publisher_.process_last_barter(e);
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
				FluxCppCore::StringUtil::setString(mkt_depth.symbol_,
					m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(
						market_depth_index).symbol_n_exch_id().symbol().c_str(), sizeof(mkt_depth.symbol_));
				FluxCppCore::StringUtil::setString(mkt_depth.exch_time_,
					m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(
						market_depth_index).exch_time().c_str(), sizeof(mkt_depth.exch_time_));
				FluxCppCore::StringUtil::setString(mkt_depth.arrival_time_,
					m_mobile_book_publisher_.m_market_depth_history_collection_.raw_market_depth_history(
						market_depth_index).arrival_time().c_str(), sizeof(mkt_depth.arrival_time_));
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
				FluxCppCore::StringUtil::setString(last_barter.symbol_n_exch_id_.symbol_,
					m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).symbol_n_exch_id().symbol().c_str(),
						sizeof(last_barter.symbol_n_exch_id_.symbol_));
				FluxCppCore::StringUtil::setString(last_barter.symbol_n_exch_id_.exch_id_,
					m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).symbol_n_exch_id().exch_id().c_str(),
						sizeof(last_barter.symbol_n_exch_id_.exch_id_));
				FluxCppCore::StringUtil::setString(last_barter.exch_time_,
					m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).exch_time().c_str(), sizeof(last_barter.exch_time_));
				FluxCppCore::StringUtil::setString(last_barter.arrival_time_,
					m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).arrival_time().c_str(), sizeof(last_barter.arrival_time_));
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
					FluxCppCore::StringUtil::setString(last_barter.market_barter_volume_.id_,
						m_mobile_book_publisher_.m_last_barter_collection_.raw_last_barter_history(
							last_barter_index).market_barter_volume().id().c_str(),
							sizeof(last_barter.market_barter_volume_.id_));
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
    Config& mr_config_;
    MobileBookPublisher m_mobile_book_publisher_;
};
