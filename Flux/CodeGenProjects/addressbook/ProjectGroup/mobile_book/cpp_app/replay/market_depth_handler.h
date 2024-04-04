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
#include "cpp_app_semaphore.h"
#include "top_of_book_handler.h"
#include "mobile_book_cache.h"
#include "utility_functions.h"


namespace mobile_book_handler {


    class MarketDepthHandler {
    public:
        explicit MarketDepthHandler(std::shared_ptr<FluxCppCore::MongoDBHandler> mongo_db_,
                                    MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> &r_websocket_server_,
                                    TopOfBookHandler &r_top_of_book_handler,
                                    mobile_book_cache::MarketDepthCache &market_depth_cache_handler,
                                    mobile_book_cache::TopOfBookCache &top_of_book_cache_handler) :
        m_sp_mongo_db_(std::move(mongo_db_)), mr_websocket_server_(r_websocket_server_),
        mr_top_of_book_handler_(r_top_of_book_handler), market_depth_cache_handler_(market_depth_cache_handler),
        m_top_of_book_cache_handler_(top_of_book_cache_handler), m_market_depth_db_codec_(m_sp_mongo_db_) {

            update_market_depth_cache_();
        }


        void insert_or_update_market_depth(const mobile_book::MarketDepth &market_depth_obj) {
            int32_t db_id;
            std::string market_depth_key;
            m_market_depth_db_codec_.insert_or_update(market_depth_obj, db_id);
            MobileBookKeyHandler::get_key_out(market_depth_obj, market_depth_key);
            m_market_depth_db_codec_.m_root_model_key_to_db_id[market_depth_key] = db_id;
        }

        void handle_md_update(mobile_book::MarketDepth &market_depth_obj) {
            market_depth_cache_handler_.update_or_create_market_depth_cache(market_depth_obj);
            insert_or_update_market_depth(market_depth_obj);
            if (market_depth_obj.position() == 0) {
                mobile_book::TopOfBook top_of_book_obj;
                top_of_book_obj.set_id(market_depth_obj.id());
                top_of_book_obj.set_symbol(market_depth_obj.symbol());
                if (market_depth_obj.side() == mobile_book::TickType::BID) {
                    top_of_book_obj.mutable_bid_quote()->set_px(market_depth_obj.px());
                    top_of_book_obj.mutable_bid_quote()->set_qty(market_depth_obj.qty());
//                    top_of_book_obj.mutable_bid_quote()->set_premium(market_depth_obj.premium());
                    top_of_book_obj.mutable_bid_quote()->set_last_update_date_time
                            (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                    top_of_book_obj.set_last_update_date_time
                            (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                } else if (market_depth_obj.side() == mobile_book::TickType::ASK) {
                    top_of_book_obj.mutable_ask_quote()->set_px(market_depth_obj.px());
                    top_of_book_obj.mutable_ask_quote()->set_qty(market_depth_obj.qty());
//                    top_of_book_obj.mutable_ask_quote()->set_premium(market_depth_obj.premium());
                    top_of_book_obj.mutable_ask_quote()->set_last_update_date_time
                            (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                    top_of_book_obj.set_last_update_date_time
                            (mobile_book_handler::MobileBookPopulateRandomValues::get_utc_time());
                } // else not required: TopOfBook only need ASK and BID

                m_top_of_book_cache_handler_.update_or_create_top_of_book_cache(top_of_book_obj, TickType_Name(market_depth_obj.side()));
                notify_semaphore.release();
                mr_top_of_book_handler_.insert_or_update_top_of_book(top_of_book_obj);
            } // else not required: for every symbol TopOfBook should be only 1
            mr_websocket_server_.NewClientCallBack(market_depth_obj, -1);
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

    protected:
        std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
        MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> &mr_websocket_server_;
        TopOfBookHandler &mr_top_of_book_handler_;
        mobile_book_cache::MarketDepthCache &market_depth_cache_handler_;
        mobile_book_cache::TopOfBookCache &m_top_of_book_cache_handler_;
        FluxCppCore::MongoDBCodec<mobile_book::MarketDepth, mobile_book::MarketDepthList> m_market_depth_db_codec_;
    };
}