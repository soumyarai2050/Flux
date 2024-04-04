#pragma once

#include "../../../../../../FluxCppCore/include/mongo_db_handler.h"
#include "last_barter_handler.h"
#include "market_depth_handler.h"

namespace mobile_book_handler {

    class HistoryManager {
    public:
        explicit HistoryManager(std::shared_ptr<FluxCppCore::MongoDBHandler> &mongo_db_,
                                LastBarterHandler &r_last_barter_handler,
                                MarketDepthHandler &r_market_depth_handler,
                                quill::Logger *logger = quill::get_logger()) :
                                m_sp_mongo_db_(std::move(mongo_db_)), mr_last_barter_handler(r_last_barter_handler),
                                mr_market_depth_handler(r_market_depth_handler), m_p_logger_(logger),
                                m_market_depth_history_db_codec_(m_sp_mongo_db_),
                                m_last_barter_db_codec_(m_sp_mongo_db_) {

            m_last_barter_db_codec_.get_all_data_from_collection(m_last_barter_collection_);
            m_market_depth_history_db_codec_.get_all_data_from_collection(m_market_depth_history_collection_);

        }

        void replay() {

            int market_depth_index = 0;
            int last_barter_index = 0;

            while (market_depth_index < m_market_depth_history_collection_.raw_market_depth_history_size() ||
                   last_barter_index < m_last_barter_collection_.raw_last_barter_history_size()) {
                if (market_depth_index < m_market_depth_history_collection_.raw_market_depth_history_size() &&
                    (last_barter_index >= m_last_barter_collection_.raw_last_barter_history_size())) {
                    mobile_book::MarketDepth market_depth;
                    // Replay market depth
                    const auto& market_depth_history =
                            m_market_depth_history_collection_.raw_market_depth_history(market_depth_index);

                    market_depth.set_id(market_depth_history.id());
                    market_depth.set_symbol(market_depth_history.symbol_n_exch_id().symbol());
                    market_depth.set_exch_time(market_depth_history.exch_time());
                    market_depth.set_arrival_time(market_depth_history.arrival_time());
                    market_depth.set_side(market_depth_history.side());
                    market_depth.set_px(market_depth_history.px());
                    market_depth.set_qty(market_depth_history.qty());
                    market_depth.set_position(market_depth_history.position());

                    mr_market_depth_handler.handle_md_update(market_depth);
                    ++market_depth_index;
                } else {
                    // Replay last barter
                    mobile_book::RawLastBarterHistory history_last_barter = m_last_barter_collection_.raw_last_barter_history(last_barter_index);
                    mobile_book::LastBarter last_barter;
                    last_barter.set_id(history_last_barter.id());
                    last_barter.mutable_symbol_n_exch_id()->set_symbol(history_last_barter.symbol_n_exch_id().symbol());
                    last_barter.mutable_symbol_n_exch_id()->set_exch_id(history_last_barter.symbol_n_exch_id().exch_id());
                    last_barter.set_exch_time(history_last_barter.exch_time());
                    last_barter.set_arrival_time(history_last_barter.arrival_time());
                    last_barter.set_px(history_last_barter.px());
                    last_barter.set_qty(history_last_barter.qty());
                    last_barter.set_premium(history_last_barter.premium());
                    last_barter.mutable_market_barter_volume()->set_id(history_last_barter.market_barter_volume().id());
                    last_barter.mutable_market_barter_volume()->set_participation_period_last_barter_qty_sum(history_last_barter.market_barter_volume().participation_period_last_barter_qty_sum());
                    last_barter.mutable_market_barter_volume()->set_applicable_period_seconds(history_last_barter.market_barter_volume().applicable_period_seconds());

                    mr_last_barter_handler.handle_last_barter_update(last_barter);
                    ++last_barter_index;
                }
            }
        }

    protected:
        std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
        LastBarterHandler &mr_last_barter_handler;
        MarketDepthHandler &mr_market_depth_handler;
        quill::Logger *m_p_logger_;

        FluxCppCore::MongoDBCodec<mobile_book::RawMarketDepthHistory, mobile_book::RawMarketDepthHistoryList>
        m_market_depth_history_db_codec_;
        FluxCppCore::MongoDBCodec<mobile_book::RawLastBarterHistory, mobile_book::RawLastBarterHistoryList> m_last_barter_db_codec_;

        mobile_book::RawLastBarterHistoryList m_last_barter_collection_;
        mobile_book::RawMarketDepthHistoryList m_market_depth_history_collection_;

    };

}
