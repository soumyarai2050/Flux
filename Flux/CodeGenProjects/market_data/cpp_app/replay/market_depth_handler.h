#pragma once

#include "quill/Quill.h"

#include "../include/market_data_mongo_db_handler.h"
#include "../../generated/CppUtilGen/market_data_constants.h"
#include "../../generated/CppUtilGen/market_data_key_handler.h"
#include "../../FluxCppCore/include/mongo_db_codec.h"
#include "../../FluxCppCore/include/base_web_client.h"
#include "../../generated/CppUtilGen/market_data_web_socket_server.h"
#include "../../generated/CppUtilGen/market_data_populate_random_values.h"
#include "../../generated/CppUtilGen/market_data_max_id_handler.h"

namespace market_data_handler {

    const std::string host_ ="127.0.0.1";
    const std::string port_ = "8040";

    class MarketDepthHandler {
    public:
        explicit MarketDepthHandler(std::shared_ptr<MarketData_MongoDBHandler> mongo_db_,
                                    quill::Logger *logger = quill::get_logger()) :
        m_sp_mongo_db_(std::move(mongo_db_)), mp_logger_(logger), m_market_depth_db_codec_(m_sp_mongo_db_),
        m_top_of_book_db_codec_(m_sp_mongo_db_), m_top_of_book_publisher_(host_, port_), m_market_depth_obj_(),
        m_websocket_server_(m_market_depth_obj_) {
            
            update_market_depth_cache_();
            update_top_of_book_cache_();

            m_market_depth_websocket_thread_ = std::thread([&]() {
                m_websocket_server_.run();
            });
            
        }

        void insert_or_update_market_depth(const market_data::MarketDepth &market_depth_obj) {
            int32_t db_id;
            std::string market_depth_key;
            m_market_depth_db_codec_.insert_or_update(market_depth_obj, db_id);
            MarketDataKeyHandler::get_key_out(market_depth_obj, market_depth_key);
            m_market_depth_db_codec_.m_root_model_key_to_db_id[market_depth_key] = db_id;
        }

        void handle_md_update(market_data::MarketDepth &market_depth_obj) {
            insert_or_update_market_depth(market_depth_obj);
            m_websocket_server_.NewClientCallBack(market_depth_obj, -1);
            int32_t db_id;
            if (market_depth_obj.position() == 0) {
                market_data::TopOfBook top_of_book_obj;
                auto found = m_top_of_book_db_codec_.m_root_model_key_to_db_id.find(market_depth_obj.symbol());
                if (found != m_top_of_book_db_codec_.m_root_model_key_to_db_id.end()) {
                    db_id = m_top_of_book_db_codec_.m_root_model_key_to_db_id.at(market_depth_obj.symbol());
                    top_of_book_obj.set_id(db_id);
                    top_of_book_obj.set_symbol(market_depth_obj.symbol());
                    if (market_depth_obj.side() == market_data::BID) {
                        top_of_book_obj.mutable_bid_quote()->set_px(market_depth_obj.px());
                        top_of_book_obj.mutable_bid_quote()->set_qty(market_depth_obj.qty());
                        top_of_book_obj.mutable_bid_quote()->set_premium(market_depth_obj.premium());
                        top_of_book_obj.mutable_ask_quote()->set_last_update_date_time
                                (market_data_handler::MarketDataPopulateRandomValues::get_utc_time());
                        top_of_book_obj.set_last_update_date_time
                                (market_data_handler::MarketDataPopulateRandomValues::get_utc_time());
                    } else if (market_depth_obj.side() == market_data::ASK) {
                        top_of_book_obj.mutable_ask_quote()->set_px(market_depth_obj.px());
                        top_of_book_obj.mutable_ask_quote()->set_qty(market_depth_obj.qty());
                        top_of_book_obj.mutable_ask_quote()->set_premium(market_depth_obj.premium());
                        top_of_book_obj.mutable_ask_quote()->set_last_update_date_time
                                (market_data_handler::MarketDataPopulateRandomValues::get_utc_time());
                        top_of_book_obj.set_last_update_date_time
                                (market_data_handler::MarketDataPopulateRandomValues::get_utc_time());
                    } // else not required: TopOfBook only need ASK and BID

                    bool status = m_top_of_book_publisher_.patch_client(top_of_book_obj);
                    if (!status) {
                        LOG_ERROR(mp_logger_, "TopOfBook patch failed: {}", top_of_book_obj.DebugString());
                    } // else not required: if patch success the no need to perform any operation

                } else {
                    top_of_book_obj.set_id(market_depth_obj.id());
                    top_of_book_obj.set_symbol(market_depth_obj.symbol());
                    if (market_depth_obj.side() == market_data::BID) {
                        top_of_book_obj.mutable_bid_quote()->set_px(market_depth_obj.px());
                        top_of_book_obj.mutable_bid_quote()->set_qty(market_depth_obj.qty());
                        top_of_book_obj.mutable_bid_quote()->set_premium(market_depth_obj.premium());
                        top_of_book_obj.mutable_bid_quote()->set_last_update_date_time
                        (market_data_handler::MarketDataPopulateRandomValues::get_utc_time());
                        top_of_book_obj.set_last_update_date_time
                        (market_data_handler::MarketDataPopulateRandomValues::get_utc_time());
                    } else if (market_depth_obj.side() == market_data::ASK) {
                        top_of_book_obj.mutable_ask_quote()->set_px(market_depth_obj.px());
                        top_of_book_obj.mutable_ask_quote()->set_qty(market_depth_obj.qty());
                        top_of_book_obj.mutable_ask_quote()->set_premium(market_depth_obj.premium());
                        top_of_book_obj.mutable_ask_quote()->set_last_update_date_time
                                (market_data_handler::MarketDataPopulateRandomValues::get_utc_time());
                        top_of_book_obj.set_last_update_date_time
                                (market_data_handler::MarketDataPopulateRandomValues::get_utc_time());
                    } // else not required: TopOfBook only need ASK and BID

                    bool status = m_top_of_book_publisher_.create_client(top_of_book_obj);
                    MarketDataMaxIdHandler::update_top_of_book_max_id(m_top_of_book_publisher_);
                    if (status) {
                        std::string key;
                        MarketDataKeyHandler::get_key_out(top_of_book_obj, key);
                        m_top_of_book_db_codec_.m_root_model_key_to_db_id[key] = top_of_book_obj.id();
                    } else {
                        LOG_ERROR(mp_logger_, "TopOfBook create failed: {}", top_of_book_obj.DebugString());
                    }
                }
            } // else not required: for every symbol TopOfBook should be only 1
        }

        ~MarketDepthHandler() {
            m_websocket_server_.shutdown();
            m_market_depth_websocket_thread_.join();
        }

    protected:
        std::shared_ptr<MarketData_MongoDBHandler> m_sp_mongo_db_;
        quill::Logger *mp_logger_;
        FluxCppCore::MongoDBCodec<market_data::MarketDepth, market_data::MarketDepthList> m_market_depth_db_codec_;
        FluxCppCore::MongoDBCodec<market_data::TopOfBook, market_data::TopOfBookList> m_top_of_book_db_codec_;

        FluxCppCore::RootModelWebClient<market_data::TopOfBook, create_top_of_book_client_url, get_top_of_book_client_url,
        get_top_of_book_max_id_client_url, put_top_of_book_client_url, patch_top_of_book_client_url,
        delete_top_of_book_client_url> m_top_of_book_publisher_;
        market_data::MarketDepth m_market_depth_obj_;

        MarketDataMarketDepthWebSocketServer<market_data::MarketDepth> m_websocket_server_;
        std::thread m_market_depth_websocket_thread_;

        void update_top_of_book_cache_() {
            market_data::TopOfBookList top_of_book_documents;
            std::vector<std::string> keys;
            m_top_of_book_db_codec_.get_all_data_from_collection(top_of_book_documents);
            MarketDataKeyHandler::get_key_list(top_of_book_documents, keys);
            for (int i = 0; i < top_of_book_documents.top_of_book_size(); ++i) {
                m_top_of_book_db_codec_.m_root_model_key_to_db_id[keys.at(i)] =
                        top_of_book_documents.top_of_book(i).id();
            }
        }
        
        void update_market_depth_cache_() {
            market_data::MarketDepthList market_depth_documents;
            std::vector<std::string> keys;
            m_market_depth_db_codec_.get_all_data_from_collection(market_depth_documents);
            MarketDataKeyHandler::get_key_list(market_depth_documents, keys);
            for (int i = 0; i < market_depth_documents.market_depth_size(); ++i) {
                m_market_depth_db_codec_.m_root_model_key_to_db_id[keys.at(i)] =
                        market_depth_documents.market_depth(i).id();
            }
        }
    };
}