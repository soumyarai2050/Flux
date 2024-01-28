#pragma once

#include "quill/Quill.h"

#include "../../../../../../FluxCppCore/include/mongo_db_handler.h"
#include "../../generated/CppUtilGen/mobile_book_constants.h"
#include "../../generated/CppUtilGen/mobile_book_key_handler.h"
#include "../../../../../../FluxCppCore/include/mongo_db_codec.h"
#include "../../../../../../FluxCppCore/include/base_web_client.h"
#include "../../generated/CppUtilGen/mobile_book_web_socket_server.h"
#include "../../generated/CppUtilGen/mobile_book_populate_random_values.h"
#include "../../generated/CppUtilGen/mobile_book_max_id_handler.h"

namespace mobile_book_handler {

    const std::string host_ ="127.0.0.1";
    const std::string port_ = "8040";

    class MarketDepthHandler {
    public:
        explicit MarketDepthHandler(std::shared_ptr<FluxCppCore::MongoDBHandler> mongo_db_,
                                    quill::Logger *logger = quill::get_logger()) :
        m_sp_mongo_db_(std::move(mongo_db_)), mp_logger_(logger), m_market_depth_db_codec_(m_sp_mongo_db_),
        m_top_of_book_db_codec_(m_sp_mongo_db_), m_top_of_book_publisher_(host_, port_),
        m_market_depth_publisher_(host_, port_), m_market_depth_obj_(),
        m_websocket_server_(m_market_depth_obj_) {
            
            update_market_depth_cache_();
            update_top_of_book_cache_();

//            m_market_depth_websocket_thread_ = std::thread([&]() {
//                m_websocket_server_.run();
//            });

        }

        void insert_or_update_market_depth_web_client(const mobile_book::MarketDepth &market_depth_obj) {
            mobile_book::MarketDepth market_depth_obj_copy = market_depth_obj;
            std::string market_depth_key;
            bool status;
            MobileBookKeyHandler::get_key_out(market_depth_obj, market_depth_key);
            auto found = m_market_depth_db_codec_.m_root_model_key_to_db_id.find(market_depth_key);
            if (found == m_market_depth_db_codec_.m_root_model_key_to_db_id.end()) {
                status = m_market_depth_publisher_.create_client(market_depth_obj_copy);
                auto db_id = m_market_depth_publisher_.get_max_id_client();
                m_market_depth_db_codec_.m_root_model_key_to_db_id[market_depth_key] = db_id;
            } else {
                auto db_id = m_market_depth_db_codec_.m_root_model_key_to_db_id.at(market_depth_key);
                market_depth_obj_copy.set_id(db_id);
                status = m_market_depth_publisher_.put_client(market_depth_obj_copy);
            }
        }

        void insert_or_update_market_depth(const mobile_book::MarketDepth &market_depth_obj) {
            int32_t db_id;
            std::string market_depth_key;
            m_market_depth_db_codec_.insert_or_update(market_depth_obj, db_id);
            MobileBookKeyHandler::get_key_out(market_depth_obj, market_depth_key);
            m_market_depth_db_codec_.m_root_model_key_to_db_id[market_depth_key] = db_id;
        }

        void handle_md_update(mobile_book::MarketDepth &market_depth_obj) {
            insert_or_update_market_depth_web_client(market_depth_obj);
//            m_websocket_server_.NewClientCallBack(market_depth_obj, -1);
            int32_t db_id;
            if (market_depth_obj.position() == 0) {
                mobile_book::TopOfBook top_of_book_obj;
                auto found = m_top_of_book_db_codec_.m_root_model_key_to_db_id.find(market_depth_obj.symbol());
                if (found != m_top_of_book_db_codec_.m_root_model_key_to_db_id.end()) {
                    db_id = m_top_of_book_db_codec_.m_root_model_key_to_db_id.at(market_depth_obj.symbol());
                    top_of_book_obj.set_id(db_id);
                    top_of_book_obj.set_symbol(market_depth_obj.symbol());
                    if (market_depth_obj.side() == mobile_book::BID) {
                        top_of_book_obj.mutable_bid_quote()->set_px(market_depth_obj.px());
                        top_of_book_obj.mutable_bid_quote()->set_qty(market_depth_obj.qty());
                        top_of_book_obj.mutable_bid_quote()->set_premium(market_depth_obj.premium());
                        top_of_book_obj.mutable_ask_quote()->set_last_update_date_time
                                (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                        top_of_book_obj.set_last_update_date_time
                                (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                    } else if (market_depth_obj.side() == mobile_book::ASK) {
                        top_of_book_obj.mutable_ask_quote()->set_px(market_depth_obj.px());
                        top_of_book_obj.mutable_ask_quote()->set_qty(market_depth_obj.qty());
                        top_of_book_obj.mutable_ask_quote()->set_premium(market_depth_obj.premium());
                        top_of_book_obj.mutable_ask_quote()->set_last_update_date_time
                                (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                        top_of_book_obj.set_last_update_date_time
                                (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                    } // else not required: TopOfBook only need ASK and BID

                    bool status = m_top_of_book_publisher_.patch_client(top_of_book_obj);
                    if (!status) {
                        LOG_ERROR(mp_logger_, "TopOfBook patch failed: {}", top_of_book_obj.DebugString());
                    } // else not required: if patch success the no need to perform any operation

                } else {
                    top_of_book_obj.set_id(market_depth_obj.id());
                    top_of_book_obj.set_symbol(market_depth_obj.symbol());
                    if (market_depth_obj.side() == mobile_book::BID) {
                        top_of_book_obj.mutable_bid_quote()->set_px(market_depth_obj.px());
                        top_of_book_obj.mutable_bid_quote()->set_qty(market_depth_obj.qty());
                        top_of_book_obj.mutable_bid_quote()->set_premium(market_depth_obj.premium());
                        top_of_book_obj.mutable_bid_quote()->set_last_update_date_time
                        (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                        top_of_book_obj.set_last_update_date_time
                        (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                    } else if (market_depth_obj.side() == mobile_book::ASK) {
                        top_of_book_obj.mutable_ask_quote()->set_px(market_depth_obj.px());
                        top_of_book_obj.mutable_ask_quote()->set_qty(market_depth_obj.qty());
                        top_of_book_obj.mutable_ask_quote()->set_premium(market_depth_obj.premium());
                        top_of_book_obj.mutable_ask_quote()->set_last_update_date_time
                                (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                        top_of_book_obj.set_last_update_date_time
                                (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                    } // else not required: TopOfBook only need ASK and BID

                    bool status = m_top_of_book_publisher_.create_client(top_of_book_obj);
                    MobileBookMaxIdHandler::update_top_of_book_max_id(m_top_of_book_publisher_);
                    if (status) {
                        std::string key;
                        MobileBookKeyHandler::get_key_out(top_of_book_obj, key);
                        m_top_of_book_db_codec_.m_root_model_key_to_db_id[key] = top_of_book_obj.id();
                    } else {
                        LOG_ERROR(mp_logger_, "TopOfBook create failed: {}", top_of_book_obj.DebugString());
                    }
                }
            } // else not required: for every symbol TopOfBook should be only 1
        }

//        ~MarketDepthHandler() {
//            m_websocket_server_.shutdown();
//            m_market_depth_websocket_thread_.join();
//        }

    protected:
        std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
        quill::Logger *mp_logger_;
        FluxCppCore::MongoDBCodec<mobile_book::MarketDepth, mobile_book::MarketDepthList> m_market_depth_db_codec_;
        FluxCppCore::MongoDBCodec<mobile_book::TopOfBook, mobile_book::TopOfBookList> m_top_of_book_db_codec_;

        FluxCppCore::RootModelWebClient<mobile_book::TopOfBook, create_top_of_book_client_url, get_top_of_book_client_url,
        get_top_of_book_max_id_client_url, put_top_of_book_client_url, patch_top_of_book_client_url,
        delete_top_of_book_client_url> m_top_of_book_publisher_;
        FluxCppCore::RootModelWebClient<mobile_book::MarketDepth, create_market_depth_client_url,
                get_market_depth_client_url, get_market_depth_max_id_client_url, put_market_depth_client_url,
                patch_market_depth_client_url, delete_market_depth_client_url> m_market_depth_publisher_;

        mobile_book::MarketDepth m_market_depth_obj_;

        MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> m_websocket_server_;
        std::thread m_market_depth_websocket_thread_;

        void update_top_of_book_cache_() {
            mobile_book::TopOfBookList top_of_book_documents;
            std::vector<std::string> keys;
            m_top_of_book_db_codec_.get_all_data_from_collection(top_of_book_documents);
            MobileBookKeyHandler::get_key_list(top_of_book_documents, keys);
            for (int i = 0; i < top_of_book_documents.top_of_book_size(); ++i) {
                m_top_of_book_db_codec_.m_root_model_key_to_db_id[keys.at(i)] =
                        top_of_book_documents.top_of_book(i).id();
            }
        }
        
        void update_market_depth_cache_() {
            mobile_book::MarketDepthList market_depth_documents;
            std::vector<std::string> keys;
            m_market_depth_db_codec_.get_all_data_from_collection(market_depth_documents);
            MobileBookKeyHandler::get_key_list(market_depth_documents, keys);
            for (int i = 0; i < market_depth_documents.market_depth_size(); ++i) {
                m_market_depth_db_codec_.m_root_model_key_to_db_id[keys.at(i)] =
                        market_depth_documents.market_depth(i).id();
            }
        }
    };
}