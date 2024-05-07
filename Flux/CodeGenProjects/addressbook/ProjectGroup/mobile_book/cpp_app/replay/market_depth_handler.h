#pragma once

#include "quill/Quill.h"

#include "../../../../../../FluxCppCore/include/mongo_db_handler.h"
#include "../../generated/CppUtilGen/mobile_book_constants.h"
#include "../../generated/CppUtilGen/mobile_book_key_handler.h"
#include "../../../../../../FluxCppCore/include/mongo_db_codec.h"
#include "../../generated/CppUtilGen/mobile_book_web_socket_server.h"
#include "../../generated/CppUtilGen/mobile_book_populate_random_values.h"
#include "cpp_app_semaphore.h"
#include "top_of_book_handler.h"
#include "mobile_book_cache.h"
#include "utility_functions.h"


namespace mobile_book_handler {


    class MarketDepthHandler {
    public:
        explicit MarketDepthHandler(std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db_,
                                    MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> &r_websocket_server_,
                                    mobile_book_handler::TopOfBookHandler &r_top_of_book_handler,
                                    mobile_book_cache::MarketDepthCache &r_market_depth_cache_handler,
                                    mobile_book_cache::TopOfBookCache &r_top_of_book_cache_handler) :
        m_sp_mongo_db_(std::move(sp_mongo_db_)), mr_websocket_server_(r_websocket_server_),
        mr_top_of_book_handler_(r_top_of_book_handler), mr_market_depth_cache_handler_(r_market_depth_cache_handler),
        mr_top_of_book_cache_handler_(r_top_of_book_cache_handler), m_market_depth_db_codec_(m_sp_mongo_db_) {

            update_market_depth_cache_();
        }


        void insert_or_update_market_depth(const mobile_book::MarketDepth &kr_market_depth_obj) {
            int32_t db_id;
            std::string market_depth_key;
            m_market_depth_db_codec_.insert_or_update(kr_market_depth_obj, db_id);
        }

        void handle_md_update(mobile_book::MarketDepth &r_market_depth_obj) {
            mr_market_depth_cache_handler_.update_or_create_market_depth_cache(r_market_depth_obj);
            insert_or_update_market_depth(r_market_depth_obj);
            mr_websocket_server_.NewClientCallBack(r_market_depth_obj, -1);
            auto date_time = MobileBookPopulateRandomValues::get_utc_time();
            if (r_market_depth_obj.position() == 0) {
                mobile_book::TopOfBook top_of_book_obj;
                top_of_book_obj.set_id(r_market_depth_obj.id());
                top_of_book_obj.set_symbol(r_market_depth_obj.symbol());
                if (r_market_depth_obj.side() == mobile_book::TickType::BID) {
                    top_of_book_obj.mutable_bid_quote()->set_px(r_market_depth_obj.px());
                    top_of_book_obj.mutable_bid_quote()->set_qty(r_market_depth_obj.qty());
                    top_of_book_obj.mutable_bid_quote()->set_last_update_date_time(date_time);
                    top_of_book_obj.set_last_update_date_time(date_time);
                } else if (r_market_depth_obj.side() == mobile_book::TickType::ASK) {
                    top_of_book_obj.mutable_ask_quote()->set_px(r_market_depth_obj.px());
                    top_of_book_obj.mutable_ask_quote()->set_qty(r_market_depth_obj.qty());
                    top_of_book_obj.mutable_ask_quote()->set_last_update_date_time(date_time);
                    top_of_book_obj.set_last_update_date_time(date_time);
                } // else not required: TopOfBook only need ASK and BID
                mr_top_of_book_cache_handler_.update_or_create_top_of_book_cache(top_of_book_obj, TickType_Name(r_market_depth_obj.side()));
                notify_semaphore.release();
                mr_top_of_book_handler_.insert_or_update_top_of_book(top_of_book_obj);

            } // else not required: for every symbol TopOfBook should be only 1
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
        mobile_book_cache::MarketDepthCache &mr_market_depth_cache_handler_;
        mobile_book_cache::TopOfBookCache &mr_top_of_book_cache_handler_;
        FluxCppCore::MongoDBCodec<mobile_book::MarketDepth, mobile_book::MarketDepthList> m_market_depth_db_codec_;
    };
}