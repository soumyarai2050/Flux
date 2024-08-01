#pragma once


#include "../../../../../../FluxCppCore/include/mongo_db_handler.h"
#include "../../generated/CppUtilGen/mobile_book_key_handler.h"
#include "../../../../../../FluxCppCore/include/mongo_db_codec.h"
#include "../../generated/CppUtilGen/mobile_book_web_socket_server.h"
#include "cpp_app_semaphore.h"
#include "top_of_book_handler.h"
#include "mobile_book_cache.h"
#include "queue_handler.h"


namespace mobile_book_handler {


    class MarketDepthHandler {
    public:
        explicit MarketDepthHandler(std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db_,
                                    MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> &r_websocket_server_,
                                    mobile_book_handler::TopOfBookHandler &r_top_of_book_handler) :
        m_sp_mongo_db_(std::move(sp_mongo_db_)), mr_websocket_server_(r_websocket_server_),
        mr_top_of_book_handler_(r_top_of_book_handler), m_market_depth_db_codec_(m_sp_mongo_db_),
        m_db_n_ws_handler_thread_{[this]{handle_db_n_ws_update();}} {

            update_market_depth_cache_();
        }

        void insert_or_update_market_depth(const mobile_book::MarketDepth &kr_market_depth_obj) {
            int32_t db_id;
            std::string market_depth_key;
            m_market_depth_db_codec_.insert_or_update(kr_market_depth_obj, db_id);
        }

        FluxCppCore::CacheOperationResult handle_md_update(mobile_book::MarketDepth &r_market_depth_obj) {

            if (!r_market_depth_obj.has_arrival_time() or !r_market_depth_obj.has_exch_time()) {
                auto date_time = FluxCppCore::get_utc_time_microseconds();
                if (!r_market_depth_obj.has_arrival_time()) {
                    r_market_depth_obj.set_arrival_time(date_time);
                }
                if (!r_market_depth_obj.has_exch_time()) {
                    r_market_depth_obj.set_exch_time(date_time);
                }
            }

            if (r_market_depth_obj.position() == 0) {
                bool top_of_book_cache_update_status{false};
                if (r_market_depth_obj.side() == mobile_book::TickType::BID) {

                    void* p_md_mutex = market_cache::MarketDepthCache::get_bid_md_mutex_from_depth(
                        r_market_depth_obj.symbol(), r_market_depth_obj.position());
                    void*  p_tob_mutex = market_cache::TopOfBookCache::get_top_of_book_mutex(
                        r_market_depth_obj.symbol());

                    if (p_md_mutex == nullptr) {
                        LOG_ERROR_IMPL(GetLogger(), "unable to get nutex for market_depth symbol: {};;; side: BID",
                            r_market_depth_obj.symbol());
                        return FluxCppCore::CacheOperationResult::MUTEX_NOT_AVAILABLE;
                    }

                    if (p_tob_mutex == nullptr) {
                        LOG_ERROR_IMPL(GetLogger(), "unable to get nutex for top_of_book symbol: {}",
                            r_market_depth_obj.symbol());
                        return FluxCppCore::CacheOperationResult::MUTEX_NOT_AVAILABLE;
                    }

                    auto md_mutex = static_cast<std::mutex*>(p_md_mutex);
                    auto top_of_book_mutex = static_cast<std::mutex*>(p_tob_mutex);
                    auto lock_status = std::try_lock(*md_mutex, *top_of_book_mutex);
                    if (lock_status != ALL_LOCKS_AVAILABE_) {
                        m_monitor_.push(r_market_depth_obj);
                        LOG_DEBUG_IMPL(GetLogger(), "Ignoring cache update lock not found;;; market_depth_obj: {}",
                            r_market_depth_obj.DebugString());
                        return FluxCppCore::CacheOperationResult::LOCK_NOT_FOUND;
                    }

                    create_top_of_book_from_md(r_market_depth_obj, m_top_of_book_obj_);
                    {
                        std::lock_guard<std::mutex> lock_md_mutex(*md_mutex, std::adopt_lock);
                        std::lock_guard<std::mutex> lock_top_of_book_mutex(*top_of_book_mutex, std::adopt_lock);
                        market_cache::MarketDepthCache::update_bid_market_depth_cache(r_market_depth_obj);
                        top_of_book_cache_update_status = market_cache::TopOfBookCache::update_top_of_book_cache(m_top_of_book_obj_);
                    }
                } else if (r_market_depth_obj.side() == mobile_book::TickType::ASK) {

                    void* p_md_mutex = market_cache::MarketDepthCache::get_ask_md_mutex_from_depth(
                        r_market_depth_obj.symbol(), r_market_depth_obj.position());
                    void*  p_tob_mutex = market_cache::TopOfBookCache::get_top_of_book_mutex(r_market_depth_obj.symbol());

                    if (p_md_mutex == nullptr) {
                        LOG_ERROR_IMPL(GetLogger(), "unable to get nutex for market_depth symbol: {};;; side: ASK",
                            r_market_depth_obj.symbol());
                        return FluxCppCore::CacheOperationResult::MUTEX_NOT_AVAILABLE;
                    }
                    if (p_tob_mutex == nullptr) {
                        LOG_ERROR_IMPL(GetLogger(), "unable to get nutex for top_of_book symbol: {}",
                            r_market_depth_obj.symbol());
                        return FluxCppCore::CacheOperationResult::MUTEX_NOT_AVAILABLE;
                    }
                    auto md_mutex = static_cast<std::mutex*>(p_md_mutex);
                    auto top_of_book_mutex = static_cast<std::mutex*>(p_tob_mutex);
                    auto lock_status = std::try_lock(*md_mutex, *top_of_book_mutex);
                    if (lock_status != ALL_LOCKS_AVAILABE_) {
                        m_monitor_.push(r_market_depth_obj);
                        LOG_DEBUG_IMPL(GetLogger(), "Ignoring cache update lock not found;;; market_depth_obj: {}",
                            r_market_depth_obj.DebugString());
                        return FluxCppCore::CacheOperationResult::LOCK_NOT_FOUND;
                    }

                    create_top_of_book_from_md(r_market_depth_obj, m_top_of_book_obj_);
                    {
                        std::lock_guard<std::mutex> lock_md_mutex(*md_mutex, std::adopt_lock);
                        std::lock_guard<std::mutex> lock_top_of_book_mutex(*top_of_book_mutex, std::adopt_lock);
                        market_cache::MarketDepthCache::update_bid_market_depth_cache(r_market_depth_obj);
                        top_of_book_cache_update_status = market_cache::TopOfBookCache::update_top_of_book_cache(m_top_of_book_obj_);
                    }
                } // else not required: TopOfBook only need ASK and BID
                if (top_of_book_cache_update_status) {notify_semaphore.release();}
                m_top_of_book_obj_.Clear();
            } else {
                if (r_market_depth_obj.side() == mobile_book::TickType::BID) {

                    void* p_md_mutex = market_cache::MarketDepthCache::get_bid_md_mutex_from_depth(
                        r_market_depth_obj.symbol(), r_market_depth_obj.position());
                    if (p_md_mutex == nullptr) {
                        LOG_ERROR_IMPL(GetLogger(), "unable to get nutex for market_depth symbol: {};;; side: BID",
                            r_market_depth_obj.symbol());
                        return FluxCppCore::CacheOperationResult::MUTEX_NOT_AVAILABLE;
                    }

                    auto md_mutex = static_cast<std::mutex*>(p_md_mutex);
                    std::unique_lock<std::mutex> lock_md_mutex(*md_mutex, std::try_to_lock_t{});
                    if (!lock_md_mutex.owns_lock()) {
                        m_monitor_.push(r_market_depth_obj);
                        LOG_DEBUG_IMPL(GetLogger(), "Ignoring cache update lock not found;;; market_depth_obj: {}",
                            r_market_depth_obj.DebugString());
                        return FluxCppCore::CacheOperationResult::LOCK_NOT_FOUND;
                    }
                    market_cache::MarketDepthCache::update_bid_market_depth_cache(r_market_depth_obj);
                } else {

                    void* p_md_mutex = market_cache::MarketDepthCache::get_ask_md_mutex_from_depth(
                        r_market_depth_obj.symbol(), r_market_depth_obj.position());
                    if (p_md_mutex == nullptr) {
                        LOG_ERROR_IMPL(GetLogger(), "unable to get nutex for market_depth symbol: {};;; side: ASk",
                            r_market_depth_obj.symbol());
                        return FluxCppCore::CacheOperationResult::MUTEX_NOT_AVAILABLE;
                    }
                    auto md_mutex = static_cast<std::mutex*>(p_md_mutex);
                    std::unique_lock<std::mutex> lock_md_mutex(*md_mutex, std::try_to_lock_t{});
                    if (!lock_md_mutex.owns_lock()) {
                        m_monitor_.push(r_market_depth_obj);
                        LOG_DEBUG_IMPL(GetLogger(), "Ignoring cache update lock not found;;; market_depth_obj: {}",
                            r_market_depth_obj.DebugString());
                        return FluxCppCore::CacheOperationResult::LOCK_NOT_FOUND;
                    }
                    market_cache::MarketDepthCache::update_ask_market_depth_cache(r_market_depth_obj);
                }
            }

            m_monitor_.push(r_market_depth_obj);
            return FluxCppCore::CacheOperationResult::SUCCESS_DB_AND_CACHE_UPDATE;

        }

    protected:
        std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
        MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> &mr_websocket_server_;
        TopOfBookHandler &mr_top_of_book_handler_;
        FluxCppCore::MongoDBCodec<mobile_book::MarketDepth, mobile_book::MarketDepthList> m_market_depth_db_codec_;
        FluxCppCore::Monitor<mobile_book::MarketDepth> m_monitor_{};
        std::jthread m_db_n_ws_handler_thread_;
        const int8_t ALL_LOCKS_AVAILABE_{-1};
        mobile_book::TopOfBook m_top_of_book_obj_{};

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

        static void create_top_of_book_from_md(const mobile_book::MarketDepth &kr_market_depth_obj, mobile_book::TopOfBook &r_top_of_book_obj_out) {

            r_top_of_book_obj_out.set_id(kr_market_depth_obj.id());
            r_top_of_book_obj_out.set_symbol(kr_market_depth_obj.symbol());
            r_top_of_book_obj_out.set_last_update_date_time(kr_market_depth_obj.exch_time());
            if (kr_market_depth_obj.side() == mobile_book::TickType::BID) {
                r_top_of_book_obj_out.mutable_bid_quote()->set_px(kr_market_depth_obj.px());
                r_top_of_book_obj_out.mutable_bid_quote()->set_qty(kr_market_depth_obj.qty());
                r_top_of_book_obj_out.mutable_bid_quote()->set_last_update_date_time(kr_market_depth_obj.exch_time());
            } else if (kr_market_depth_obj.side() == mobile_book::TickType::ASK) {
                r_top_of_book_obj_out.mutable_ask_quote()->set_px(kr_market_depth_obj.px());
                r_top_of_book_obj_out.mutable_ask_quote()->set_qty(kr_market_depth_obj.qty());
                r_top_of_book_obj_out.mutable_ask_quote()->set_last_update_date_time(kr_market_depth_obj.exch_time());
            }
        }

        void handle_db_n_ws_update() {
            mobile_book::TopOfBook top_of_book;
            mobile_book::MarketDepth market_depth;

            while (true) {
                auto pop_status = m_monitor_.pop(market_depth);
                if (pop_status == FluxCppCore::QueueStatus::DATA_CONSUMED) {
                    insert_or_update_market_depth(market_depth);
                    if (market_depth.position() == 0) {
                        create_top_of_book_from_md(market_depth, top_of_book);
                        mr_top_of_book_handler_.insert_or_update_top_of_book(top_of_book);
                    }

                    mr_websocket_server_.NewClientCallBack(market_depth, -1);
                    market_depth.Clear();
                    top_of_book.Clear();
                }

                if (shutdown_db_n_ws_thread) {
                    return;
                }
            }
        }
    };
}