#pragma once

#include "../../../../../../FluxCppCore/include/mongo_db_handler.h"
#include "../../../../../../FluxCppCore/include/mongo_db_codec.h"
#include "../../../../../../FluxCppCore/include/base_web_client.h"
#include "../../generated/CppUtilGen/mobile_book_populate_random_values.h"
#include "../../generated/CppUtilGen/mobile_book_max_id_handler.h"
#include "mobile_book_mongo_db_codec.h"
#include "cpp_app_semaphore.h"
#include "top_of_book_handler.h"


namespace mobile_book_handler {

    class LastBarterHandler {
    public:
        explicit LastBarterHandler(std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db_,
                                  MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> &r_last_barter_websocket_server_,
                                  TopOfBookHandler &r_top_of_book_handler,
                                  mobile_book_cache::LastBarterCache &r_last_barter_cache_handler,
                                  mobile_book_cache::TopOfBookCache &r_top_of_book_cache_handler) :
        m_sp_mongo_db_(std::move(sp_mongo_db_)), mr_last_barter_websocket_server_(r_last_barter_websocket_server_),
        mr_top_of_book_handler_(r_top_of_book_handler),
        mr_last_barter_cache_handler_(r_last_barter_cache_handler),
        mr_top_of_book_cache_handler_(r_top_of_book_cache_handler),
        m_last_barter_db_codec_(m_sp_mongo_db_) {}

        void handle_last_barter_update(mobile_book::LastBarter &r_last_barter_obj) {
            int32_t last_barter_inserted_id;
            std::string last_barter_key;
            auto date_time = MobileBookPopulateRandomValues::get_utc_time();

            mobile_book::TopOfBook top_of_book_obj;
            top_of_book_obj.set_id(r_last_barter_obj.id());
            top_of_book_obj.set_symbol(r_last_barter_obj.symbol_n_exch_id().symbol());
            top_of_book_obj.mutable_last_barter()->set_px(r_last_barter_obj.px());
            top_of_book_obj.mutable_last_barter()->set_qty(r_last_barter_obj.qty());
            top_of_book_obj.mutable_last_barter()->set_premium(last_barter_obj.premium());
            top_of_book_obj.mutable_last_barter()->set_last_update_date_time(date_time);
            top_of_book_obj.add_market_barter_volume()->CopyFrom(r_last_barter_obj.market_barter_volume());
            top_of_book_obj.set_last_update_date_time(date_time);
            r_last_barter_obj.set_arrival_time(date_time);
            r_last_barter_obj.set_exch_time(date_time);

            mr_last_barter_cache_handler_.update_or_create_last_barter_cache(r_last_barter_obj);
            mr_top_of_book_cache_handler_.update_or_create_top_of_book_cache(top_of_book_obj);
            notify_semaphore.release();

            bsoncxx::builder::basic::document bson_doc{};
            prepare_doc(r_last_barter_obj, bson_doc);
            // std::unique_lock<std>
            bool status = m_last_barter_db_codec_.insert(bson_doc, last_barter_key, last_barter_inserted_id);
            assert(status);

            mr_top_of_book_handler_.insert_or_update_top_of_book(top_of_book_obj);
            mr_last_barter_websocket_server_.NewClientCallBack(r_last_barter_obj, -1);
        }

    protected:
        std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
        MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> &mr_last_barter_websocket_server_;
        TopOfBookHandler &mr_top_of_book_handler_;
        mobile_book_cache::LastBarterCache &mr_last_barter_cache_handler_;
        mobile_book_cache::TopOfBookCache &mr_top_of_book_cache_handler_;
        FluxCppCore::MongoDBCodec<mobile_book::LastBarter, mobile_book::LastBarterList> m_last_barter_db_codec_;

        void update_last_barter_cache() {
            mobile_book::LastBarterList last_barter_obj_list;
            std::vector<std::string> keys;
            m_last_barter_db_codec_.get_all_data_from_collection(last_barter_obj_list);
            ::MobileBookKeyHandler::get_key_list(last_barter_obj_list, keys);

            for (int i = 0; i < last_barter_obj_list.last_barter_size(); ++i) {
                m_last_barter_db_codec_.m_root_model_key_to_db_id[keys.at(i)] = last_barter_obj_list.last_barter(i).id();
            }
        }
    };
}