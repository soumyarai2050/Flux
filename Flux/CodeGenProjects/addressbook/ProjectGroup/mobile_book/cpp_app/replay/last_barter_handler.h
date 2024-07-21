#pragma once

#include <unchoreed_map>

#include "../../../../../../FluxCppCore/include/mongo_db_handler.h"
#include "../../../../../../FluxCppCore/include/mongo_db_codec.h"
#include "../../../../../../FluxCppCore/include/base_web_client.h"
#include "mobile_book_mongo_db_codec.h"
#include "cpp_app_semaphore.h"
#include "top_of_book_handler.h"
#include "queue_handler.h"


namespace mobile_book_handler {

    class LastBarterHandler {
    public:
        explicit LastBarterHandler(std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db_,
                                  MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> &r_last_barter_websocket_server_,
                                  TopOfBookHandler &r_top_of_book_handler) :
        m_sp_mongo_db_(std::move(sp_mongo_db_)), mr_last_barter_websocket_server_(r_last_barter_websocket_server_),
        mr_top_of_book_handler_(r_top_of_book_handler),
        m_last_barter_db_codec_(m_sp_mongo_db_), m_db_n_ws_update_handler_thread_{[this](){handle_db_n_ws_update();}} {}

        FluxCppCore::CacheOperationResult handle_last_barter_update(mobile_book::LastBarter &r_last_barter_obj) {

            if (!r_last_barter_obj.has_arrival_time() or !r_last_barter_obj.has_exch_time()) {
                auto date_time = FluxCppCore::get_utc_time_microseconds();
                if (!r_last_barter_obj.has_arrival_time()) {
                    r_last_barter_obj.set_arrival_time(date_time);
                }
                if (!r_last_barter_obj.has_exch_time()) {
                    r_last_barter_obj.set_exch_time(date_time);
                }
            }

            void* p_lt_mutex = market_cache::LastBarterCache::get_last_barter_mutex(
                    r_last_barter_obj.symbol_n_exch_id().symbol());
            void* p_tob_mutex = market_cache::TopOfBookCache::get_top_of_book_mutex(
                r_last_barter_obj.symbol_n_exch_id().symbol());

            if (p_lt_mutex == nullptr) {
                LOG_ERROR_IMPL(GetLogger(), "unable to get nutex for last_barter symbol: {}", r_last_barter_obj.symbol_n_exch_id().symbol());
                return FluxCppCore::CacheOperationResult::MUTEX_NOT_AVAILABLE;
            }

            if (p_tob_mutex == nullptr) {
                LOG_ERROR_IMPL(GetLogger(), "unable to get nutex for top-of_book symbol: {}", r_last_barter_obj.symbol_n_exch_id().symbol());
                return FluxCppCore::CacheOperationResult::MUTEX_NOT_AVAILABLE;
            }

            auto last_barter_mutex = static_cast<std::mutex*>(p_lt_mutex);
            auto top_of_book_mutex = static_cast<std::mutex*>(p_tob_mutex);

            auto lock_status = std::try_lock(*last_barter_mutex, *top_of_book_mutex);

            if (lock_status != ALL_LOCKS_AVAILABLE_) {
                m_monito_.push(r_last_barter_obj);
                LOG_DEBUG_IMPL(GetLogger(), "Ignoring cache update lock not found;;; last_barter_obj: {}",
                    r_last_barter_obj.DebugString());
                return FluxCppCore::CacheOperationResult::LOCK_NOT_FOUND;
            }

            bool top_of_book_cache_update_result{false};

            create_top_of_book_obj_from_last_barter(r_last_barter_obj, m_top_of_book_obj_);
            {
                std::lock_guard<std::mutex> last_barter_lock(*last_barter_mutex, std::adopt_lock);
                std::lock_guard<std::mutex> top_of_book_lock(*top_of_book_mutex, std::adopt_lock);
                market_cache::LastBarterCache::update_last_barter_cache(r_last_barter_obj);
                top_of_book_cache_update_result =
                    market_cache::TopOfBookCache::update_top_of_book_cache(m_top_of_book_obj_);
            }

            if (top_of_book_cache_update_result) {
                notify_semaphore.release();
            }

            m_top_of_book_obj_.Clear();
            m_monito_.push(r_last_barter_obj);
            return FluxCppCore::CacheOperationResult::SUCCESS_DB_AND_CACHE_UPDATE;
        }

    protected:
        std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
        MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> &mr_last_barter_websocket_server_;
        TopOfBookHandler &mr_top_of_book_handler_;
        FluxCppCore::MongoDBCodec<mobile_book::LastBarter, mobile_book::LastBarterList> m_last_barter_db_codec_;
        FluxCppCore::Monitor<mobile_book::LastBarter> m_monito_{};
        std::jthread m_db_n_ws_update_handler_thread_;
        const int8_t ALL_LOCKS_AVAILABLE_{-1};
        mobile_book::TopOfBook m_top_of_book_obj_{};


        void update_last_barter_cache() {
            mobile_book::LastBarterList last_barter_obj_list;
            std::vector<std::string> keys;
            m_last_barter_db_codec_.get_all_data_from_collection(last_barter_obj_list);
            ::MobileBookKeyHandler::get_key_list(last_barter_obj_list, keys);

            for (int i = 0; i < last_barter_obj_list.last_barter_size(); ++i) {
                m_last_barter_db_codec_.m_root_model_key_to_db_id[keys.at(i)] = last_barter_obj_list.last_barter(i).id();
            }
        }

        static void create_top_of_book_obj_from_last_barter(const mobile_book::LastBarter &kr_last_barter_obj,
            mobile_book::TopOfBook &r_top_of_book_obj_out) {

            r_top_of_book_obj_out.set_id(kr_last_barter_obj.id());
            r_top_of_book_obj_out.set_symbol(kr_last_barter_obj.symbol_n_exch_id().symbol());
            r_top_of_book_obj_out.mutable_last_barter()->set_px(kr_last_barter_obj.px());
            r_top_of_book_obj_out.mutable_last_barter()->set_qty(kr_last_barter_obj.qty());
            if (kr_last_barter_obj.has_premium()) {
                r_top_of_book_obj_out.mutable_last_barter()->set_premium(kr_last_barter_obj.premium());
            }
            r_top_of_book_obj_out.mutable_last_barter()->set_last_update_date_time(kr_last_barter_obj.exch_time());
            r_top_of_book_obj_out.set_last_update_date_time(kr_last_barter_obj.exch_time());
            if (kr_last_barter_obj.has_market_barter_volume()) {
                r_top_of_book_obj_out.add_market_barter_volume()->CopyFrom(kr_last_barter_obj.market_barter_volume());
            }

        }

        void handle_db_n_ws_update() {
            std::string last_barter_key;
            int32_t last_barter_id;
            bsoncxx::builder::basic::document bson_doc{};
            mobile_book::LastBarter last_barter;
            while(true)
            {
                auto pop_status = m_monito_.pop(last_barter);
                if(pop_status == FluxCppCore::QueueStatus::DATA_CONSUMED) {
                    MobileBookKeyHandler::get_key_out(last_barter, last_barter_key);
                    prepare_doc(last_barter, bson_doc);
                    bool status = m_last_barter_db_codec_.insert(bson_doc, last_barter_key, last_barter_id);
                    assert(status);
                    mobile_book::TopOfBook top_of_book_obj;
                    create_top_of_book_obj_from_last_barter(last_barter, top_of_book_obj);
                    mr_top_of_book_handler_.insert_or_update_top_of_book(top_of_book_obj);
                    mr_last_barter_websocket_server_.NewClientCallBack(last_barter, -1);

                    last_barter.Clear();
                    bson_doc.clear();
                    last_barter_key.clear();
                }

                if (shutdown_db_n_ws_thread) {
                    return;
                }
            }
        }
    };
}