#pragma once

#include "../include/market_data_mongo_db_handler.h"
#include "last_trade_handler.h"
#include "market_depth_handler.h"

namespace market_data_handler {

    class HistoryManager {
    public:
        explicit HistoryManager(std::shared_ptr<MarketData_MongoDBHandler> &mongo_db_,
                                LastTradeHandler &r_last_trade_handler,
                                MarketDepthHandler &r_market_depth_handler,
                                quill::Logger *logger = quill::get_logger()) :
                                m_sp_mongo_db_(std::move(mongo_db_)), mr_last_trade_handler(r_last_trade_handler),
                                mr_market_depth_handler(r_market_depth_handler), m_p_logger_(logger),
                                m_market_depth_history_db_codec_(m_sp_mongo_db_),
                                m_last_trade_db_codec_(m_sp_mongo_db_) {

            m_last_trade_db_codec_.get_all_data_from_collection(m_last_trade_collection_);
            m_market_depth_history_db_codec_.get_all_data_from_collection(m_market_depth_history_collection_);

        }

        void replay() {

            int market_depth_index = 0;
            int last_trade_index = 0;

            while (market_depth_index < m_market_depth_history_collection_.raw_market_depth_history_size() ||
                   last_trade_index < m_last_trade_collection_.last_trade_size()) {
                if (market_depth_index < m_market_depth_history_collection_.raw_market_depth_history_size() &&
                    (last_trade_index >= m_last_trade_collection_.last_trade_size())) {
                    market_data::MarketDepth market_depth;
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
                    // Replay last trade
                    market_data::LastTrade last_trade = m_last_trade_collection_.last_trade(last_trade_index);
                    mr_last_trade_handler.handle_last_trade_update(last_trade);
                    ++last_trade_index;
                }
            }
        }

    protected:
        std::shared_ptr<MarketData_MongoDBHandler> m_sp_mongo_db_;
        LastTradeHandler &mr_last_trade_handler;
        MarketDepthHandler &mr_market_depth_handler;
        quill::Logger *m_p_logger_;

        FluxCppCore::MongoDBCodec<market_data::RawMarketDepthHistory, market_data::RawMarketDepthHistoryList>
        m_market_depth_history_db_codec_;
        FluxCppCore::MongoDBCodec<market_data::LastTrade, market_data::LastTradeList> m_last_trade_db_codec_;

        market_data::LastTradeList m_last_trade_collection_;
        market_data::RawMarketDepthHistoryList m_market_depth_history_collection_;

    };

}
