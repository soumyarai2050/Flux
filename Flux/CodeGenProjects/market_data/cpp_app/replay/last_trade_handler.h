#pragma once

#include "../../cpp_app/include/market_data_mongo_db_handler.h"
#include "../../FluxCppCore/include/mongo_db_codec.h"
#include "../../FluxCppCore/include/base_web_client.h"
#include "../../generated/CppUtilGen/market_data_populate_random_values.h"
#include "../../generated/CppUtilGen/market_data_max_id_handler.h"

namespace market_data_handler {

    const std::string host ="127.0.0.1";
    const std::string port = "8040";

    class LastTradeHandler {
    public:
        explicit LastTradeHandler(std::shared_ptr<MarketData_MongoDBHandler> mongo_db_,
                                  quill::Logger *logger = quill::get_logger()) :
        m_sp_mongo_db_(std::move(mongo_db_)), mp_logger_(logger), m_last_trade_db_codec_(m_sp_mongo_db_),
        m_top_of_book_db_codec_(m_sp_mongo_db_), m_top_of_book_publisher_(host, port) {
            update_top_of_book_cache();
        }

        void handle_last_trade_update(market_data::LastTrade &last_trade_obj) {
            int32_t last_trade_inserted_id;
            int32_t db_id;
            m_last_trade_db_codec_.insert_or_update(last_trade_obj, last_trade_inserted_id);
            
            market_data::TopOfBook top_of_book_obj;
            std::string symbol_key = last_trade_obj.symbol_n_exch_id().symbol() + "_";
            auto found = m_top_of_book_db_codec_.m_root_model_key_to_db_id.find(symbol_key);
            if (found != m_top_of_book_db_codec_.m_root_model_key_to_db_id.end()) {
                db_id = m_top_of_book_db_codec_.m_root_model_key_to_db_id.at(symbol_key);
                top_of_book_obj.set_id(db_id);
                top_of_book_obj.set_symbol(last_trade_obj.symbol_n_exch_id().symbol());
                top_of_book_obj.mutable_last_trade()->set_px(last_trade_obj.px());
                top_of_book_obj.mutable_last_trade()->set_qty(last_trade_obj.qty());
                top_of_book_obj.mutable_last_trade()->set_premium(last_trade_obj.premium());
                top_of_book_obj.mutable_last_trade()->set_last_update_date_time
                (MarketDataPopulateRandomValues::get_utc_time());
                top_of_book_obj.add_market_trade_volume()->CopyFrom(last_trade_obj.market_trade_volume());
                top_of_book_obj.set_last_update_date_time(MarketDataPopulateRandomValues::get_utc_time());
                bool status = m_top_of_book_publisher_.patch_client(top_of_book_obj);
                if (!status) {
                    LOG_ERROR(mp_logger_, "TopOfBook patch failed {}", top_of_book_obj.DebugString());
                }
            } else {
                top_of_book_obj.set_id(MarketDataMaxIdHandler::c_top_of_book_max_id_handler.get_next_id());
                top_of_book_obj.set_symbol(last_trade_obj.symbol_n_exch_id().symbol());
                top_of_book_obj.mutable_last_trade()->set_px(last_trade_obj.px());
                top_of_book_obj.mutable_last_trade()->set_qty(last_trade_obj.qty());
                top_of_book_obj.mutable_last_trade()->set_premium(last_trade_obj.premium());
                top_of_book_obj.mutable_last_trade()->set_last_update_date_time
                        (MarketDataPopulateRandomValues::get_utc_time());
                top_of_book_obj.add_market_trade_volume()->CopyFrom(last_trade_obj.market_trade_volume());
                top_of_book_obj.set_last_update_date_time(MarketDataPopulateRandomValues::get_utc_time());
                bool status = m_top_of_book_publisher_.create_client(top_of_book_obj);
                if (status) {
                    std::string key;
                    MarketDataKeyHandler::get_key_out(top_of_book_obj, key);
                    m_top_of_book_db_codec_.m_root_model_key_to_db_id[key] = top_of_book_obj.id();
                } else {
                    LOG_ERROR(mp_logger_, "TopOfBook create failed: {}", top_of_book_obj.DebugString());
                }
            }
        }

    protected:
        std::shared_ptr<MarketData_MongoDBHandler> m_sp_mongo_db_;
        quill::Logger *mp_logger_;
        FluxCppCore::MongoDBCodec<market_data::LastTrade, market_data::LastTradeList> m_last_trade_db_codec_;
        FluxCppCore::MongoDBCodec<market_data::TopOfBook, market_data::TopOfBookList> m_top_of_book_db_codec_;

        FluxCppCore::RootModelWebClient<market_data::TopOfBook, create_top_of_book_client_url, get_top_of_book_client_url,
                get_top_of_book_max_id_client_url, put_top_of_book_client_url, patch_top_of_book_client_url,
                delete_top_of_book_client_url> m_top_of_book_publisher_;

        void update_top_of_book_cache() {
            market_data::TopOfBookList top_of_book_documents;
            std::vector<std::string> keys;
            m_top_of_book_db_codec_.get_all_data_from_collection(top_of_book_documents);
            MarketDataKeyHandler::get_key_list(top_of_book_documents, keys);
            for (int i = 0; i < top_of_book_documents.top_of_book_size(); ++i) {
                m_top_of_book_db_codec_.m_root_model_key_to_db_id[keys.at(i)] =
                        top_of_book_documents.top_of_book(i).id();
            }
        }
    };
}