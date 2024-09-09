#pragma once

#include "mobile_book_consumer.h"
#include "../../../../../../FluxCppCore/include/mongo_db_handler.h"


namespace mobile_book_handler {

    class HistoryManager {
    public:
        explicit HistoryManager(std::shared_ptr<FluxCppCore::MongoDBHandler> &mongo_db_,
            MobileBookConsumer &mobile_book_consumer) :
        m_sp_mongo_db_(std::move(mongo_db_)), r_mobile_book_consumer_(mobile_book_consumer),
        m_market_depth_history_db_codec_(m_sp_mongo_db_), m_last_barter_db_codec_(m_sp_mongo_db_) {

            m_last_barter_db_codec_.get_all_data_from_collection(m_last_barter_collection_);
            m_market_depth_history_db_codec_.get_all_data_from_collection(m_market_depth_history_collection_);

        }

        void replay() const {
            int market_depth_index = 0;
            int last_barter_index = 0;

            while (market_depth_index < m_market_depth_history_collection_.raw_market_depth_history_size() ||
                   last_barter_index < m_last_barter_collection_.raw_last_barter_history_size()) {
                if (market_depth_index < m_market_depth_history_collection_.raw_market_depth_history_size() &&
                    (last_barter_index >= m_last_barter_collection_.raw_last_barter_history_size())) {
                    std::string exch_time;
                    std::string arrival_time;
                    FluxCppCore::format_time(m_market_depth_history_collection_.raw_market_depth_history(
                        market_depth_index).exch_time(), exch_time);
                    FluxCppCore::format_time(m_market_depth_history_collection_.raw_market_depth_history(
                        market_depth_index).arrival_time(), arrival_time);
                    char side;
                    if (m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).side() ==
                        mobile_book::TickType::BID) {
                        side = 'B';
                    } else {
                        side = 'A';
                    }

                    PyMktDepth mkt_depth{m_market_depth_history_collection_.raw_market_depth_history(
                        market_depth_index).symbol_n_exch_id().symbol().c_str(), exch_time.c_str(),
                        arrival_time.c_str(), side,
                        m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).position(),
                        static_cast<double>(m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).px()),
                        m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).qty(),
                        "", false, 0.0, 0, 0.0};

                    r_mobile_book_consumer_.process_market_depth(mkt_depth);
                    ++market_depth_index;
                } else {
                    // Replay last barter
                    std::string exch_time;
                    std::string arrival_time;
                    FluxCppCore::format_time(m_last_barter_collection_.raw_last_barter_history(
                        last_barter_index).exch_time(), exch_time);
                    FluxCppCore::format_time(m_last_barter_collection_.raw_last_barter_history(
                        last_barter_index).arrival_time(), arrival_time);

                    PyLastBarter last_barter{{m_last_barter_collection_.raw_last_barter_history(
                        last_barter_index).symbol_n_exch_id().symbol().c_str(),
                        m_last_barter_collection_.raw_last_barter_history(
                            last_barter_index).symbol_n_exch_id().exch_id().c_str()}, exch_time.c_str(),
                        arrival_time.c_str(), static_cast<double>(
                            m_last_barter_collection_.raw_last_barter_history(last_barter_index).px()),
                        m_last_barter_collection_.raw_last_barter_history(last_barter_index).qty(),
                        m_last_barter_collection_.raw_last_barter_history(last_barter_index).premium(),
                        {m_last_barter_collection_.raw_last_barter_history(
                            last_barter_index).market_barter_volume().id().c_str(),
                            m_last_barter_collection_.raw_last_barter_history(
                                last_barter_index).market_barter_volume().participation_period_last_barter_qty_sum(),
                            m_last_barter_collection_.raw_last_barter_history(
                                last_barter_index).market_barter_volume().applicable_period_seconds()}};

                    r_mobile_book_consumer_.process_last_barter(last_barter);

                    ++last_barter_index;
                }
            }
        }

    protected:
        std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
        MobileBookConsumer &r_mobile_book_consumer_;
        FluxCppCore::MongoDBCodec<mobile_book::RawMarketDepthHistory, mobile_book::RawMarketDepthHistoryList>
        m_market_depth_history_db_codec_;
        FluxCppCore::MongoDBCodec<mobile_book::RawLastBarterHistory, mobile_book::RawLastBarterHistoryList> m_last_barter_db_codec_;

        mobile_book::RawLastBarterHistoryList m_last_barter_collection_;
        mobile_book::RawMarketDepthHistoryList m_market_depth_history_collection_;

    };

}
