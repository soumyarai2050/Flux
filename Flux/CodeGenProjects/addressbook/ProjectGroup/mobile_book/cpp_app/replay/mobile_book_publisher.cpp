#include "mobile_book_publisher.h"

#include "cpp_app_shared_resource.h"
#include "../include/md_utility_functions.h"
#include "mobile_book_web_n_ws_server.h"

void inline log_md(const MarketDepthQueueElement& kr_market_depth_queue_element, const char* log_msg) {
    LOG_INFO_IMPL(GetCppAppLogger(), "{} to write data: {};;; to SHM", log_msg,
        std::format("symbol: {}, Side: {}, exch_time: {}, px: {}, qty: {}, position: {}",
            kr_market_depth_queue_element.symbol_, kr_market_depth_queue_element.side_,
            FluxCppCore::time_in_utc_str(kr_market_depth_queue_element.exch_time_),
            kr_market_depth_queue_element.px_, kr_market_depth_queue_element.qty_,
            kr_market_depth_queue_element.position_));
}

void inline log_lt(const LastBarterQueueElement& kr_last_barter_queue_element, const char* log_msg) {
    LOG_INFO_IMPL(GetCppAppLogger(), "{} to write data: {};;; to SHM", log_msg,
        std::format("symbol: {}, px: {}, qty: {}, exch_time: {}",
            kr_last_barter_queue_element.symbol_n_exch_id_.symbol_, kr_last_barter_queue_element.px_,
            kr_last_barter_queue_element.qty_, FluxCppCore::time_in_utc_str(kr_last_barter_queue_element.exch_time_)));
}

MobileBookPublisher::MobileBookPublisher(Config& config, std::shared_ptr<FluxCppCore::MongoDBHandler> mongo_db_handler) :
    mr_config_(config),
    m_sp_mongo_db_handler_(mongo_db_handler), m_market_depth_codec_(m_sp_mongo_db_handler_),
    m_last_barter_codec_(m_sp_mongo_db_handler_), m_top_of_book_codec_(m_sp_mongo_db_handler_),
    m_raw_market_depth_history_codec_(m_sp_mongo_db_handler_), m_raw_last_barter_history_codec_(m_sp_mongo_db_handler_),
    m_combined_server_(nullptr){

    initialize_shm();
    m_raw_last_barter_history_codec_.get_all_data_from_collection(m_raw_last_barter_history_list_);
    m_raw_market_depth_history_codec_.get_all_data_from_collection(m_raw_market_depth_history_list_);
    update_market_depth_db_cache();
    update_top_of_book_db_cache();
    initialize_webclient();
    m_combined_server_ = new MobileBookWebNWsServer(mr_config_, this);
    m_combined_server_->register_route_handler(std::make_shared<FluxCppCore::MarketDepthRouteHandler>(
    	mr_config_.m_market_depth_ws_route_, m_market_depth_codec_));
    m_combined_server_->register_route_handler(std::make_shared<FluxCppCore::LastBarterRouteHandler>(
    	mr_config_.m_last_barter_ws_route_, m_last_barter_codec_));
    m_combined_server_->register_route_handler(std::make_shared<FluxCppCore::TopOfBookRouteHandler>(
    	mr_config_.m_top_of_book_ws_route_, m_top_of_book_codec_));
    start_monitor_threads();
}

void MobileBookPublisher::cleanup() {
	switch (mr_config_.m_market_depth_level_) {
	    case 1: {
	        static_cast<SharedMemoryManager<ShmSymbolCache<1>>*>(m_shm_manager_)->clean_shm();
	        break;
	    }
	    case 5: {
            static_cast<SharedMemoryManager<ShmSymbolCache<5>>*>(m_shm_manager_)->clean_shm();
	        break;
        }
	    case 10: {
	        static_cast<SharedMemoryManager<ShmSymbolCache<10>>*>(m_shm_manager_)->clean_shm();
	        break;
	    }
	    case 15: {
	        static_cast<SharedMemoryManager<ShmSymbolCache<15>>*>(m_shm_manager_)->clean_shm();
	        break;
	    }
	    case 20: {
            static_cast<SharedMemoryManager<ShmSymbolCache<20>>*>(m_shm_manager_)->clean_shm();
	        break;
        }
	    default: {
	        LOG_ERROR_IMPL(GetCppAppLogger(), "Unsupported market depth level: {};;; supported levels are: "
                                              "1, 5, 10, 15, 20", mr_config_.m_market_depth_level_);
            break;
	    }
	}
    if (m_combined_server_) {
    	m_combined_server_->cleanup();
    }
}

void MobileBookPublisher::process_market_depth(const MarketDepthQueueElement& kr_market_depth_queue_element) {
    if (kr_market_depth_queue_element.symbol_ != mr_config_.m_leg_1_symbol_ &&
        kr_market_depth_queue_element.symbol_ != mr_config_.m_leg_2_symbol_) {
        return;
    }

    // Update symbol-specific caches
    auto update_symbol_cache = [&](auto& symbol_cache) {
        ++symbol_cache.update_counter;
        update_market_depth_cache(kr_market_depth_queue_element, symbol_cache);
        mobile_book_handler::compute_cumulative_fields_from_market_depth_elements(
            symbol_cache, kr_market_depth_queue_element
        );
    };

    switch (mr_config_.m_market_depth_level_) {
        case 1: {
            auto shm_cache = static_cast<ShmSymbolCache<1>*>(m_shm_symbol_cache_);
            if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_1_symbol_) {
                update_symbol_cache(shm_cache->m_leg_1_data_shm_cache_);
            }
            if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_2_symbol_) {
                update_symbol_cache(shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<1>>*>(m_shm_manager_);
                auto result = shm_manager->write_to_shared_memory(*shm_cache);
                log_md(kr_market_depth_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
            }
            break;
        }
        case 5: {
            auto shm_cache = static_cast<ShmSymbolCache<5>*>(m_shm_symbol_cache_);
            if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_1_symbol_) {
                update_symbol_cache(shm_cache->m_leg_1_data_shm_cache_);
            }
            if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_2_symbol_) {
                update_symbol_cache(shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<5>>*>(m_shm_manager_);
                auto result = shm_manager->write_to_shared_memory(*shm_cache);
                log_md(kr_market_depth_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
            }
            break;
        }
        case 10: {
            auto shm_cache = static_cast<ShmSymbolCache<10>*>(m_shm_symbol_cache_);
            if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_1_symbol_) {
                update_symbol_cache(shm_cache->m_leg_1_data_shm_cache_);
            }
            if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_2_symbol_) {
                update_symbol_cache(shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<10>>*>(m_shm_manager_);
                auto result = shm_manager->write_to_shared_memory(*shm_cache);
                log_md(kr_market_depth_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
            }
            break;
        }
        case 15: {
            auto shm_cache = static_cast<ShmSymbolCache<15>*>(m_shm_symbol_cache_);
            if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_1_symbol_) {
                update_symbol_cache(shm_cache->m_leg_1_data_shm_cache_);
            }
            if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_2_symbol_) {
                update_symbol_cache(shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<15>>*>(m_shm_manager_);
                auto result = shm_manager->write_to_shared_memory(*shm_cache);
                log_md(kr_market_depth_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
            }
            break;
        }
        case 20: {
            auto shm_cache = static_cast<ShmSymbolCache<20>*>(m_shm_symbol_cache_);
            if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_1_symbol_) {
                update_symbol_cache(shm_cache->m_leg_1_data_shm_cache_);
            }
            if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_2_symbol_) {
                update_symbol_cache(shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<20>>*>(m_shm_manager_);
                auto result = shm_manager->write_to_shared_memory(*shm_cache);
                log_md(kr_market_depth_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
            }
            break;
        }
        default: {
            LOG_ERROR_IMPL(GetCppAppLogger(), "Unsupported market depth level: {};;; supported levels are: "
                                              "1, 5, 10, 15, 20", mr_config_.m_market_depth_level_);
            break;
        }
    }

    MarketDepth market_depth{};
    populate_market_depth(kr_market_depth_queue_element, market_depth);

    // Update market depth database if PRE policy
    if (mr_config_.m_market_depth_db_update_publish_policy_ == PublishPolicy::PRE) {
        std::string md_key;
        MobileBookKeyHandler::get_key_out(market_depth, md_key);
        auto found = m_market_depth_codec_.m_root_model_key_to_db_id.find(md_key);
        if (found == m_market_depth_codec_.m_root_model_key_to_db_id.end()) {
            market_depth.id_ = m_market_depth_codec_.get_next_insert_id();
            m_market_depth_codec_.insert(market_depth);
            m_market_depth_codec_.m_root_model_key_to_db_id[md_key] = market_depth.id_;
        } else {
            market_depth.id_ = found->second;
            m_market_depth_codec_.patch(market_depth);
        }
        // m_market_depth_codec_.insert_or_update(market_depth);
    }

    // Handle top of book for first position
    if (market_depth.position_ == 0) {
        TopOfBook top_of_book;
        top_of_book.id_ = market_depth.id_;
        top_of_book.symbol_ = market_depth.symbol_;
        top_of_book.last_update_date_time_ = market_depth.exch_time_;
        top_of_book.is_last_update_date_time_set_ = true;

        auto& quote = (market_depth.side_ == "BID") ? top_of_book.bid_quote_ : top_of_book.ask_quote_;

        quote.px_ = market_depth.px_;
        quote.qty_ = market_depth.qty_;
        quote.is_qty_set_ = true;
        quote.is_px_set_ = true;
        quote.is_last_update_date_time_set_ = true;
        quote.last_update_date_time_ = market_depth.exch_time_;

        if (market_depth.side_ == "BID") {
            top_of_book.is_bid_quote_set_ = true;
        } else {
            top_of_book.is_ask_quote_set_ = true;
        }

        if (mr_config_.m_top_of_book_db_update_publish_policy_ == PublishPolicy::PRE) {
            std::string tob_key;
            MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
            auto found = m_top_of_book_codec_.m_root_model_key_to_db_id.find(tob_key);
            if (found == m_top_of_book_codec_.m_root_model_key_to_db_id.end()) {
                top_of_book.id_ = m_top_of_book_codec_.get_next_insert_id();
                m_top_of_book_codec_.insert(top_of_book);
                m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
            } else {
                top_of_book.id_ = found->second;
                m_top_of_book_codec_.patch(top_of_book);
            }
            // m_top_of_book_codec_.insert_or_update(top_of_book);
        }

        if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::PRE) {
            auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
            if (db_id == -1) {
                if (!m_tob_web_client_.value().create_client(top_of_book)) {
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Failed to crerate client top_of_book;;; id: {}, symbol: {}",
                        top_of_book.id_, top_of_book.symbol_);
                }
                std::string tob_key;
                MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
                m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
            } else {
                top_of_book.id_ = db_id;
                if (!m_tob_web_client_.value().patch_client(top_of_book)) {
                   LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to patch client top_of_book;;; id: {}, symbol: {}",
                       top_of_book.id_, top_of_book.symbol_);
                }
            }
            // if (m_top_of_book_codec_.m_root_model_key_to_db_id.find())
        }

        if (mr_config_.m_top_of_book_ws_update_publish_policy_ == PublishPolicy::PRE) {
            auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
            top_of_book.id_ = db_id;
            top_of_book.market_barter_volume_.clear();
            m_top_of_book_codec_.get_data_by_id_from_collection(top_of_book, db_id);
            boost::json::object tob_json;
            if (MobileBookObjectToJson::object_to_json(top_of_book, tob_json)) {
                m_combined_server_->publish_to_route(mr_config_.m_top_of_book_ws_route_,
                    boost::json::serialize(tob_json));
            } else {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Failed to serialize top_of_book;;; id: {}, symbol: {}",
                    top_of_book.id_, top_of_book.symbol_);
            }
        }
    }

    if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_last_barter_db_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_last_barter_http_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_last_barter_ws_update_publish_policy_ == PublishPolicy::POST) {

        switch (mr_config_.m_market_depth_level_) {
            case 1: {
                auto shm_cache = static_cast<ShmSymbolCache<1>*>(m_shm_symbol_cache_);
                const auto& md_array = (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) ?
                    ((kr_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_1_data_shm_cache_.bid_market_depths_
                        : shm_cache->m_leg_1_data_shm_cache_.ask_market_depths_) :
                ((kr_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_2_data_shm_cache_.bid_market_depths_
                    : shm_cache->m_leg_2_data_shm_cache_.ask_market_depths_);

                for (size_t i = kr_market_depth_queue_element.position_; i < md_array.size(); ++i) {
                    if (!md_array[i].is_px_set_) break;
                    m_market_depth_queue_element_list_.push_back(md_array[i]);
                }
                m_market_depth_monitor_.push(m_market_depth_queue_element_list_);
                m_market_depth_queue_element_list_.clear();
                break;
            } case 5: {
                auto shm_cache = static_cast<ShmSymbolCache<5>*>(m_shm_symbol_cache_);
                const auto& md_array = (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) ?
                    ((kr_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_1_data_shm_cache_.bid_market_depths_
                        : shm_cache->m_leg_1_data_shm_cache_.ask_market_depths_)
                : ((kr_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_2_data_shm_cache_.bid_market_depths_
                    : shm_cache->m_leg_2_data_shm_cache_.ask_market_depths_);

                for (size_t i = kr_market_depth_queue_element.position_; i < md_array.size(); ++i) {
                    if (!md_array[i].is_px_set_) break;
                    m_market_depth_queue_element_list_.push_back(md_array[i]);
                }
                m_market_depth_monitor_.push(m_market_depth_queue_element_list_);
                m_market_depth_queue_element_list_.clear();
                break;
            }
            case 10: {
                auto shm_cache = static_cast<ShmSymbolCache<10>*>(m_shm_symbol_cache_);
                const auto& md_array = (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) ?
                    ((kr_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_1_data_shm_cache_.bid_market_depths_
                        : shm_cache->m_leg_1_data_shm_cache_.ask_market_depths_)
                : ((kr_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_2_data_shm_cache_.bid_market_depths_
                    : shm_cache->m_leg_2_data_shm_cache_.ask_market_depths_);

                for (size_t i = kr_market_depth_queue_element.position_; i < md_array.size(); ++i) {
                    if (!md_array[i].is_px_set_) break;
                    m_market_depth_queue_element_list_.push_back(md_array[i]);
                }
                m_market_depth_monitor_.push(m_market_depth_queue_element_list_);
                m_market_depth_queue_element_list_.clear();
                break;
            }
            case 15: {
                auto shm_cache = static_cast<ShmSymbolCache<15>*>(m_shm_symbol_cache_);
                const auto& md_array = (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) ?
                    ((kr_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_1_data_shm_cache_.bid_market_depths_
                        : shm_cache->m_leg_1_data_shm_cache_.ask_market_depths_)
                : ((kr_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_2_data_shm_cache_.bid_market_depths_
                    : shm_cache->m_leg_2_data_shm_cache_.ask_market_depths_);

                for (size_t i = kr_market_depth_queue_element.position_; i < md_array.size(); ++i) {
                    if (!md_array[i].is_px_set_) break;
                    m_market_depth_queue_element_list_.push_back(md_array[i]);
                }
                m_market_depth_monitor_.push(m_market_depth_queue_element_list_);
                m_market_depth_queue_element_list_.clear();
                break;
            }
            case 20: {
                auto shm_cache = static_cast<ShmSymbolCache<20>*>(m_shm_symbol_cache_);
                const auto& md_array = (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) ?
                    ((kr_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_1_data_shm_cache_.bid_market_depths_
                        : shm_cache->m_leg_1_data_shm_cache_.ask_market_depths_)
                : ((kr_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_2_data_shm_cache_.bid_market_depths_
                    : shm_cache->m_leg_2_data_shm_cache_.ask_market_depths_);

                for (size_t i = kr_market_depth_queue_element.position_; i < md_array.size(); ++i) {
                    if (!md_array[i].is_px_set_) break;
                    m_market_depth_queue_element_list_.push_back(md_array[i]);
                }
                m_market_depth_monitor_.push(m_market_depth_queue_element_list_);
                m_market_depth_queue_element_list_.clear();
                break;
            }
            default: {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Unsupported market depth level: {};;; supported levels are: "
                                              "1, 5, 10, 15, 20", mr_config_.m_market_depth_level_);
                break;
            }
        }
	}
}

void MobileBookPublisher::process_market_depth(const MarketDepth& kr_market_depth) {

    MarketDepthQueueElement market_depth_queue_element;

    market_depth_queue_element.id_ = kr_market_depth.id_;
    market_depth_queue_element.side_ = kr_market_depth.side_[0];
    market_depth_queue_element.px_ = kr_market_depth.px_;
    market_depth_queue_element.is_px_set_ = kr_market_depth.is_px_set_;
    market_depth_queue_element.qty_ = kr_market_depth.qty_;
    market_depth_queue_element.is_qty_set_ = kr_market_depth.is_qty_set_;
    market_depth_queue_element.position_ = kr_market_depth.position_;
    market_depth_queue_element.is_smart_depth_ = kr_market_depth.is_smart_depth_;
    market_depth_queue_element.is_is_smart_depth_set_ = kr_market_depth.is_is_smart_depth_set_;
    market_depth_queue_element.cumulative_notional_ = kr_market_depth.cumulative_notional_;
    market_depth_queue_element.is_cumulative_notional_set_ = kr_market_depth.is_cumulative_notional_set_;
    market_depth_queue_element.cumulative_qty_ = kr_market_depth.cumulative_qty_;
    market_depth_queue_element.is_cumulative_qty_set_ = kr_market_depth.is_cumulative_qty_set_;
    market_depth_queue_element.cumulative_avg_px_ = kr_market_depth.cumulative_avg_px_;
    market_depth_queue_element.is_cumulative_avg_px_set_ = kr_market_depth.is_cumulative_avg_px_set_;

    market_depth_queue_element.exch_time_ = kr_market_depth.exch_time_;
    market_depth_queue_element.arrival_time_ = kr_market_depth.arrival_time_;

	FluxCppCore::StringUtil::setString(market_depth_queue_element.symbol_, kr_market_depth.symbol_);
	if (kr_market_depth.is_market_maker_set_) {
		FluxCppCore::StringUtil::setString(market_depth_queue_element.market_maker_, kr_market_depth.market_maker_);
		market_depth_queue_element.is_market_maker_set_ = true;
	}

	process_market_depth(market_depth_queue_element);
}

void MobileBookPublisher::process_last_barter(const LastBarterQueueElement& kr_last_barter_queue_element) {
    if (kr_last_barter_queue_element.symbol_n_exch_id_.symbol_ != mr_config_.m_leg_1_symbol_ &&
        kr_last_barter_queue_element.symbol_n_exch_id_.symbol_ != mr_config_.m_leg_2_symbol_) {
        return;
    }

    LastBarter last_barter{
        .id_ = kr_last_barter_queue_element.id_,
        .symbol_n_exch_id_{kr_last_barter_queue_element.symbol_n_exch_id_.symbol_, kr_last_barter_queue_element.symbol_n_exch_id_.exch_id_},
        .exch_time_ = kr_last_barter_queue_element.exch_time_,
        .arrival_time_ = kr_last_barter_queue_element.arrival_time_,
        .px_ = kr_last_barter_queue_element.px_,
        .qty_ = kr_last_barter_queue_element.qty_,
        .premium_ = kr_last_barter_queue_element.premium_,
        .is_premium_set_ = kr_last_barter_queue_element.is_premium_set_,
        .market_barter_volume_{kr_last_barter_queue_element.market_barter_volume_.id_,
            kr_last_barter_queue_element.market_barter_volume_.participation_period_last_barter_qty_sum_,
            kr_last_barter_queue_element.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_,
            kr_last_barter_queue_element.market_barter_volume_.applicable_period_seconds_,
            kr_last_barter_queue_element.market_barter_volume_.is_applicable_period_seconds_set_},
        .is_market_barter_volume_set_ = kr_last_barter_queue_element.is_market_barter_volume_set_
    };

    switch (mr_config_.m_market_depth_level_) {
        case 1: {
            auto shm_cache = static_cast<ShmSymbolCache<1>*>(m_shm_symbol_cache_);
            if (last_barter.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
                ++shm_cache->m_leg_1_data_shm_cache_.update_counter;
                update_last_barter_cache(kr_last_barter_queue_element,
                    shm_cache->m_leg_1_data_shm_cache_);
            }
            if (last_barter.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
                ++shm_cache->m_leg_2_data_shm_cache_.update_counter;
                update_last_barter_cache(kr_last_barter_queue_element,
                    shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<1>>*>(m_shm_manager_);
                auto result = shm_manager->write_to_shared_memory(*shm_cache);
                log_lt(kr_last_barter_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
            }
            break;
        }
        case 5: {
            auto shm_cache = static_cast<ShmSymbolCache<5>*>(m_shm_symbol_cache_);
            if (last_barter.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
                ++shm_cache->m_leg_1_data_shm_cache_.update_counter;
                update_last_barter_cache(kr_last_barter_queue_element,
                    shm_cache->m_leg_1_data_shm_cache_);
            }
            if (last_barter.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
                ++shm_cache->m_leg_2_data_shm_cache_.update_counter;
                update_last_barter_cache(kr_last_barter_queue_element,
                    shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<5>>*>(m_shm_manager_);
                auto result = shm_manager->write_to_shared_memory(*shm_cache);
                log_lt(kr_last_barter_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
            }
            break;
        }
        case 10: {
            auto shm_cache = static_cast<ShmSymbolCache<10>*>(m_shm_symbol_cache_);
            if (last_barter.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
                ++shm_cache->m_leg_1_data_shm_cache_.update_counter;
                update_last_barter_cache(kr_last_barter_queue_element,
                    shm_cache->m_leg_1_data_shm_cache_);
            }
            if (last_barter.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
                ++shm_cache->m_leg_2_data_shm_cache_.update_counter;
                update_last_barter_cache(kr_last_barter_queue_element,
                    shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<10>>*>(m_shm_manager_);
                auto result = shm_manager->write_to_shared_memory(*shm_cache);
                log_lt(kr_last_barter_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
            }
            break;
        }
        case 15: {
            auto shm_cache = static_cast<ShmSymbolCache<15>*>(m_shm_symbol_cache_);
            if (last_barter.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
                ++shm_cache->m_leg_1_data_shm_cache_.update_counter;
                update_last_barter_cache(kr_last_barter_queue_element,
                    shm_cache->m_leg_1_data_shm_cache_);
            }
            if (last_barter.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
                ++shm_cache->m_leg_2_data_shm_cache_.update_counter;
                update_last_barter_cache(kr_last_barter_queue_element,
                    shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<15>>*>(m_shm_manager_);
                auto result = shm_manager->write_to_shared_memory(*shm_cache);
                log_lt(kr_last_barter_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
            }
            break;
        }
        case 20: {
            auto shm_cache = static_cast<ShmSymbolCache<20>*>(m_shm_symbol_cache_);
            if (last_barter.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
                ++shm_cache->m_leg_1_data_shm_cache_.update_counter;
                update_last_barter_cache(kr_last_barter_queue_element,
                    shm_cache->m_leg_1_data_shm_cache_);
            }
            if (last_barter.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
                ++shm_cache->m_leg_2_data_shm_cache_.update_counter;
                update_last_barter_cache(kr_last_barter_queue_element,
                    shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<20>>*>(m_shm_manager_);
                auto result = shm_manager->write_to_shared_memory(*shm_cache);
                log_lt(kr_last_barter_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
            }
            break;
        }
        default: {
            LOG_ERROR_IMPL(GetCppAppLogger(), "Unsupported market depth level: {};;; supported levels are: "
                                              "1, 5, 10, 15, 20", mr_config_.m_market_depth_level_);
            break;
        }
    }

    if (mr_config_.m_last_barter_db_update_publish_policy_ == PublishPolicy::PRE) {
        last_barter.id_ = m_last_barter_codec_.get_next_insert_id();
        m_last_barter_codec_.insert(last_barter);
    }

    if (mr_config_.m_last_barter_ws_update_publish_policy_ == PublishPolicy::PRE) {
        boost::json::object last_barter_json;
        if (MobileBookObjectToJson::object_to_json(last_barter, last_barter_json)) {
            m_combined_server_->publish_to_route(mr_config_.m_last_barter_ws_route_,
                boost::json::serialize(last_barter_json));
        } else {
            LOG_ERROR_IMPL(GetCppAppLogger(), "Failed to serialize last barter;;; id: {}, symbol: {}", last_barter.id_,
                last_barter.symbol_n_exch_id_.symbol_);
        }
    }

    if (mr_config_.m_last_barter_http_update_publish_policy_ == PublishPolicy::PRE) {
        if(!m_lt_web_client_.value().create_client(last_barter)) {
            LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to create client last_barter;;; id: {}, symbol: {}",
                last_barter.id_, last_barter.symbol_n_exch_id_.symbol_);
        }
    }

    TopOfBook top_of_book;
    top_of_book.id_ = last_barter.id_;
    top_of_book.symbol_ = last_barter.symbol_n_exch_id_.symbol_;
    top_of_book.last_update_date_time_ = last_barter.exch_time_;
    top_of_book.is_last_update_date_time_set_ = true;
    top_of_book.total_bartering_security_size_ = std::numeric_limits<int64_t>::min();
    top_of_book.is_total_bartering_security_size_set_ = false;
    top_of_book.last_barter_.px_ = last_barter.px_;
    top_of_book.last_barter_.is_px_set_ = true;
    top_of_book.last_barter_.qty_ = last_barter.qty_;
    top_of_book.last_barter_.is_qty_set_ = true;
    top_of_book.last_barter_.last_update_date_time_ = last_barter.exch_time_;
    top_of_book.last_barter_.is_last_update_date_time_set_ = true;
    if (last_barter.is_premium_set_) {
        top_of_book.last_barter_.premium_ = last_barter.premium_;
        top_of_book.last_barter_.is_premium_set_ = true;
    }

    if (last_barter.is_market_barter_volume_set_) {
        top_of_book.market_barter_volume_.push_back(last_barter.market_barter_volume_);
        top_of_book.is_market_barter_volume_set_ = true;
    }

    if (mr_config_.m_top_of_book_db_update_publish_policy_  == PublishPolicy::PRE) {
        std::string tob_key;
        MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
        auto found = m_top_of_book_codec_.m_root_model_key_to_db_id.find(tob_key);
        if (found == m_top_of_book_codec_.m_root_model_key_to_db_id.end()) {
            top_of_book.id_ = m_top_of_book_codec_.get_next_insert_id();
            m_top_of_book_codec_.insert(top_of_book);
            m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
        } else {
            top_of_book.id_ = found->second;
            m_top_of_book_codec_.patch(top_of_book);
        }
    }

    if (mr_config_.m_top_of_book_ws_update_publish_policy_ == PublishPolicy::PRE) {
        auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
        top_of_book.id_ = db_id;
        top_of_book.market_barter_volume_.clear();
        m_top_of_book_codec_.get_data_by_id_from_collection(top_of_book, db_id);
        boost::json::object tob_json;
        if (MobileBookObjectToJson::object_to_json(top_of_book, tob_json)) {
            m_combined_server_->publish_to_route(mr_config_.m_top_of_book_ws_route_,
                boost::json::serialize(tob_json));
        } else {
            LOG_ERROR_IMPL(GetCppAppLogger(), "Failed to serialize top_of_book;;; id: {}, symbol: {}", top_of_book.id_,
                top_of_book.symbol_);
        }
    }

    if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::PRE) {
        auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
        if (db_id == -1) {
            if(!m_tob_web_client_.value().create_client(top_of_book)) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to create client top_of_book;;; id: {}, symbol: {}",
                    top_of_book.id_, top_of_book.symbol_);
            }
            std::string tob_key;
            MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
            m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
        } else {
            top_of_book.id_ = db_id;
            if (!m_tob_web_client_.value().patch_client(top_of_book)) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to patch client top_of_book;;; id: {}, symbol: {}",
                    top_of_book.id_, top_of_book.symbol_);
            }
        }
        // if (m_top_of_book_codec_.m_root_model_key_to_db_id.find())
    }

    if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_last_barter_db_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_last_barter_http_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_last_barter_ws_update_publish_policy_ == PublishPolicy::POST) {

		m_last_barter_monitor_.push(kr_last_barter_queue_element);
	}
}

void MobileBookPublisher::process_last_barter(const LastBarter& kr_last_barter) {
    LastBarterQueueElement last_barter{};

    last_barter.id_ = kr_last_barter.id_;
	FluxCppCore::StringUtil::setString(last_barter.symbol_n_exch_id_.symbol_, kr_last_barter.symbol_n_exch_id_.symbol_);
	FluxCppCore::StringUtil::setString(last_barter.symbol_n_exch_id_.exch_id_, kr_last_barter.symbol_n_exch_id_.exch_id_);
    last_barter.exch_time_ = kr_last_barter.exch_time_;
    last_barter.arrival_time_ = kr_last_barter.arrival_time_;

    last_barter.px_ = kr_last_barter.px_;
    last_barter.qty_ = kr_last_barter.qty_;

    if (kr_last_barter.is_premium_set_) {
        last_barter.premium_ = kr_last_barter.premium_;
        last_barter.is_premium_set_ = true;
    }

	if (kr_last_barter.is_market_barter_volume_set_) {
		FluxCppCore::StringUtil::setString(last_barter.market_barter_volume_.id_, kr_last_barter.market_barter_volume_.id_);
        if (kr_last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_) {
            last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_ =
                kr_last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_;
            last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = true;
        }

		if (kr_last_barter.market_barter_volume_.is_applicable_period_seconds_set_) {
            last_barter.market_barter_volume_.applicable_period_seconds_ = kr_last_barter.market_barter_volume_.applicable_period_seconds_;
            last_barter.market_barter_volume_.is_applicable_period_seconds_set_ = true;
        }
	    last_barter.is_market_barter_volume_set_ = true;
	}

    process_last_barter(last_barter);
}

template<size_t N>
void MobileBookPublisher::update_market_depth_cache(const MarketDepthQueueElement& kr_market_depth_queue_element,
	MDContainer<N>& r_mobile_book_cache_out) const {

    if (kr_market_depth_queue_element.side_ == 'B') {
        r_mobile_book_cache_out.bid_market_depths_[kr_market_depth_queue_element.position_] = kr_market_depth_queue_element;
    }

    if (kr_market_depth_queue_element.side_ == 'A') {
        r_mobile_book_cache_out.ask_market_depths_[kr_market_depth_queue_element.position_] = kr_market_depth_queue_element;
    }

    if (kr_market_depth_queue_element.position_ == 0) {
        r_mobile_book_cache_out.top_of_book_.id_ = kr_market_depth_queue_element.id_;
        FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.symbol_,  kr_market_depth_queue_element.symbol_);
        r_mobile_book_cache_out.top_of_book_.last_update_date_time_ = kr_market_depth_queue_element.exch_time_;
        r_mobile_book_cache_out.top_of_book_.is_last_update_date_time_set_ = true;

        r_mobile_book_cache_out.top_of_book_.total_bartering_security_size_ = std::numeric_limits<int64_t>::min();
        r_mobile_book_cache_out.top_of_book_.is_total_bartering_security_size_set_ = false;

        if (kr_market_depth_queue_element.side_ == 'B') {
			r_mobile_book_cache_out.top_of_book_.is_bid_quote_set_ = true;
			r_mobile_book_cache_out.top_of_book_.bid_quote_.px_ = kr_market_depth_queue_element.px_;
			r_mobile_book_cache_out.top_of_book_.bid_quote_.is_px_set_ = kr_market_depth_queue_element.is_px_set_;
			r_mobile_book_cache_out.top_of_book_.bid_quote_.qty_ = kr_market_depth_queue_element.qty_;
			r_mobile_book_cache_out.top_of_book_.bid_quote_.is_qty_set_ = kr_market_depth_queue_element.is_qty_set_;
			r_mobile_book_cache_out.top_of_book_.bid_quote_.premium_ = 0.0;
			r_mobile_book_cache_out.top_of_book_.bid_quote_.is_premium_set_ = false;
			r_mobile_book_cache_out.top_of_book_.bid_quote_.last_update_date_time_ = kr_market_depth_queue_element.exch_time_;
			r_mobile_book_cache_out.top_of_book_.bid_quote_.is_last_update_date_time_set_ = true;
		}

		if (kr_market_depth_queue_element.side_ == 'A') {
			r_mobile_book_cache_out.top_of_book_.is_ask_quote_set_ = true;
			r_mobile_book_cache_out.top_of_book_.ask_quote_.px_ = kr_market_depth_queue_element.px_;
			r_mobile_book_cache_out.top_of_book_.ask_quote_.is_px_set_ = kr_market_depth_queue_element.is_px_set_;
			r_mobile_book_cache_out.top_of_book_.ask_quote_.qty_ = kr_market_depth_queue_element.qty_;
			r_mobile_book_cache_out.top_of_book_.ask_quote_.is_qty_set_ = kr_market_depth_queue_element.is_qty_set_;
			r_mobile_book_cache_out.top_of_book_.ask_quote_.premium_ = 0.0;
			r_mobile_book_cache_out.top_of_book_.ask_quote_.is_premium_set_ = false;
			r_mobile_book_cache_out.top_of_book_.ask_quote_.last_update_date_time_ = kr_market_depth_queue_element.exch_time_;
			r_mobile_book_cache_out.top_of_book_.ask_quote_.is_last_update_date_time_set_ = true;
		}
    }
}

template<size_t N>
void MobileBookPublisher::update_last_barter_cache(const LastBarterQueueElement& kr_last_barter_queue_element,
	MDContainer<N>& r_mobile_book_cache_out) const {
	// LastBarter
	r_mobile_book_cache_out.last_barter_ = kr_last_barter_queue_element;

	// TopOfBook
	FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.symbol_,
		kr_last_barter_queue_element.symbol_n_exch_id_.symbol_);
	r_mobile_book_cache_out.top_of_book_.last_update_date_time_ = kr_last_barter_queue_element.exch_time_;

	r_mobile_book_cache_out.top_of_book_.is_last_update_date_time_set_ = true;
	r_mobile_book_cache_out.top_of_book_.total_bartering_security_size_ = std::numeric_limits<int64_t>::min();
	r_mobile_book_cache_out.top_of_book_.is_total_bartering_security_size_set_ = false;

	r_mobile_book_cache_out.top_of_book_.is_last_barter_set_ = true;
	r_mobile_book_cache_out.top_of_book_.last_barter_.px_ = kr_last_barter_queue_element.px_;
	r_mobile_book_cache_out.top_of_book_.last_barter_.is_px_set_ = true;
	r_mobile_book_cache_out.top_of_book_.last_barter_.qty_ = kr_last_barter_queue_element.qty_;
	r_mobile_book_cache_out.top_of_book_.last_barter_.is_qty_set_ = true;
	r_mobile_book_cache_out.top_of_book_.last_barter_.premium_ = kr_last_barter_queue_element.premium_;
	r_mobile_book_cache_out.top_of_book_.last_barter_.is_premium_set_ = kr_last_barter_queue_element.is_premium_set_;
	r_mobile_book_cache_out.top_of_book_.last_barter_.last_update_date_time_ = kr_last_barter_queue_element.exch_time_;
	r_mobile_book_cache_out.top_of_book_.last_barter_.is_last_update_date_time_set_ = true;

    if (kr_last_barter_queue_element.is_market_barter_volume_set_) {
        FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.market_barter_volume_.id_,
            kr_last_barter_queue_element.market_barter_volume_.id_);

        if (kr_last_barter_queue_element.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_) {
            r_mobile_book_cache_out.top_of_book_.market_barter_volume_.participation_period_last_barter_qty_sum_ =
                kr_last_barter_queue_element.market_barter_volume_.participation_period_last_barter_qty_sum_;
            r_mobile_book_cache_out.top_of_book_.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = true;
        }

        if (kr_last_barter_queue_element.market_barter_volume_.is_applicable_period_seconds_set_) {
            r_mobile_book_cache_out.top_of_book_.market_barter_volume_.applicable_period_seconds_ =
                kr_last_barter_queue_element.market_barter_volume_.applicable_period_seconds_;
            r_mobile_book_cache_out.top_of_book_.market_barter_volume_.is_applicable_period_seconds_set_ = true;
        }
        r_mobile_book_cache_out.top_of_book_.is_market_barter_volume_set_  = true;
    }
}

void MobileBookPublisher::populate_market_depth(
    const MarketDepthQueueElement& kr_market_depth_queue_element, MarketDepth& r_market_depth) {

    r_market_depth.id_ = kr_market_depth_queue_element.id_;
    r_market_depth.symbol_ = kr_market_depth_queue_element.symbol_;
    r_market_depth.exch_time_ = kr_market_depth_queue_element.exch_time_;

    r_market_depth.arrival_time_ = kr_market_depth_queue_element.arrival_time_;

    if (kr_market_depth_queue_element.side_ == 'B') {
        r_market_depth.side_ = "BID";
    } else {
        r_market_depth.side_ = "ASK";
    }

    if (kr_market_depth_queue_element.is_px_set_) {
        r_market_depth.px_ = kr_market_depth_queue_element.px_;
        r_market_depth.is_px_set_ = true;
    }

    if (kr_market_depth_queue_element.is_qty_set_) {
        r_market_depth.qty_ = kr_market_depth_queue_element.qty_;
        r_market_depth.is_qty_set_ = true;
    }
    r_market_depth.position_  = kr_market_depth_queue_element.position_;

    if (kr_market_depth_queue_element.is_market_maker_set_) {
        r_market_depth.market_maker_ = kr_market_depth_queue_element.market_maker_;
        r_market_depth.is_market_maker_set_ = true;
    }

    if (kr_market_depth_queue_element.is_is_smart_depth_set_) {
        r_market_depth.is_smart_depth_ = kr_market_depth_queue_element.is_smart_depth_;
        r_market_depth.is_is_smart_depth_set_ = true;
    }

    if (kr_market_depth_queue_element.is_cumulative_notional_set_) {
        r_market_depth.cumulative_notional_ = kr_market_depth_queue_element.cumulative_notional_;
        r_market_depth.is_cumulative_notional_set_ = true;
    }

    if (kr_market_depth_queue_element.is_cumulative_qty_set_) {
        r_market_depth.cumulative_qty_ = kr_market_depth_queue_element.cumulative_qty_;
        r_market_depth.is_cumulative_qty_set_ = true;
    }

    if (kr_market_depth_queue_element.is_cumulative_avg_px_set_) {
        r_market_depth.cumulative_avg_px_ = kr_market_depth_queue_element.cumulative_avg_px_;
        r_market_depth.is_cumulative_avg_px_set_ = true;
    }

}

void MobileBookPublisher::update_market_depth_db_cache() {
    MarketDepthList market_depth_list;
    m_market_depth_codec_.get_all_data_from_collection(market_depth_list);
    std::vector<std::string> market_depth_key_list;
    MobileBookKeyHandler::get_key_list(market_depth_list, market_depth_key_list);
    for (size_t i{0}; i < market_depth_list.market_depth_.size(); ++i) {
        m_market_depth_codec_.m_root_model_key_to_db_id[market_depth_key_list[i]] =
            market_depth_list.market_depth_.at(i).id_;
    }
}

void MobileBookPublisher::update_top_of_book_db_cache() {
    TopOfBookList top_of_book_list;
    m_top_of_book_codec_.get_all_data_from_collection(top_of_book_list);
    std::vector<std::string> top_of_book_key_list;
    MobileBookKeyHandler::get_key_list(top_of_book_list, top_of_book_key_list);
    for (size_t i{0}; i < top_of_book_list.top_of_book_.size(); ++i) {
        m_top_of_book_codec_.m_root_model_key_to_db_id[top_of_book_key_list[i]] =
            top_of_book_list.top_of_book_.at(i).id_;
    }
}

void MobileBookPublisher::initialize_websocket_servers() {
    if (mr_config_.m_market_depth_ws_update_publish_policy_ != PublishPolicy::OFF) {
        m_web_socket_server_.emplace(mobile_book_handler::host,
            mr_config_.m_ws_port_,
            std::chrono::seconds(mobile_book_handler::connection_timeout));
    }
}

void MobileBookPublisher::market_depth_consumer() {
    std::vector<MarketDepthQueueElement> market_depth_queue_element_list;
    while (keepRunning) {
        auto status = m_market_depth_monitor_.pop(market_depth_queue_element_list, std::chrono::milliseconds(
            mobile_book_handler::connection_timeout));

        if (status == FluxCppCore::QueueStatus::DATA_CONSUMED) {
            for (const auto& market_depth_queue_element : market_depth_queue_element_list) {
                if (market_depth_queue_element.symbol_ != mr_config_.m_leg_1_symbol_ &&
                    market_depth_queue_element.symbol_ != mr_config_.m_leg_2_symbol_) {
                    continue;
                }
                MarketDepth market_depth{};
                if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::POST) {
                    switch (mr_config_.m_market_depth_level_) {
                        case 1: {
                            auto shm_cache = static_cast<ShmSymbolCache<1>*>(m_shm_symbol_cache_);
                            auto shm_manger = static_cast<SharedMemoryManager<ShmSymbolCache<1>>*>(m_shm_manager_);
                            auto result = shm_manger->write_to_shared_memory(*shm_cache);
                            log_md(market_depth_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
                            break;
                        }
                        case 5: {
                            auto shm_cache = static_cast<ShmSymbolCache<5>*>(m_shm_symbol_cache_);
                            auto shm_manger = static_cast<SharedMemoryManager<ShmSymbolCache<5>>*>(m_shm_manager_);
                            auto result = shm_manger->write_to_shared_memory(*shm_cache);
                            log_md(market_depth_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
                            break;
                        }
                        case 10: {
                            auto shm_cache = static_cast<ShmSymbolCache<10>*>(m_shm_symbol_cache_);
                            auto shm_manger = static_cast<SharedMemoryManager<ShmSymbolCache<10>>*>(m_shm_manager_);
                            auto result = shm_manger->write_to_shared_memory(*shm_cache);
                            log_md(market_depth_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
                            break;
                        } case 15: {
                            auto shm_cache = static_cast<ShmSymbolCache<15>*>(m_shm_symbol_cache_);
                            auto shm_manger = static_cast<SharedMemoryManager<ShmSymbolCache<15>>*>(m_shm_manager_);
                            auto result = shm_manger->write_to_shared_memory(*shm_cache);
                            log_md(market_depth_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
                            break;
                        }
                        case 20: {
                            auto shm_cache = static_cast<ShmSymbolCache<20>*>(m_shm_symbol_cache_);
                            auto shm_manger = static_cast<SharedMemoryManager<ShmSymbolCache<20>>*>(m_shm_manager_);
                            auto result = shm_manger->write_to_shared_memory(*shm_cache);
                            log_md(market_depth_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
                            break;
                        }
                        default: {
                            LOG_ERROR_IMPL(GetCppAppLogger(), "Unsupported market depth level: {};;; supported levels are: "
                                              "1, 5, 10, 15, 20", mr_config_.m_market_depth_level_);
                            break;
                        }
                    }
                }
                populate_market_depth(market_depth_queue_element, market_depth);

                if (mr_config_.m_market_depth_db_update_publish_policy_ == PublishPolicy::POST) {
                    std::string md_key;
                    MobileBookKeyHandler::get_key_out(market_depth, md_key);
                    auto found = m_market_depth_codec_.m_root_model_key_to_db_id.find(md_key);
                    if (found == m_market_depth_codec_.m_root_model_key_to_db_id.end()) {
                        market_depth.id_ = m_market_depth_codec_.get_next_insert_id();
                        m_market_depth_codec_.insert(market_depth);
                        m_market_depth_codec_.m_root_model_key_to_db_id[md_key] = market_depth.id_;
                    } else {
                        market_depth.id_ = found->second;
                        m_market_depth_codec_.patch(market_depth);
                    }
                    // auto db_id  = m_market_depth_codec_.insert_or_update(market_depth);
                    // market_depth.id_ = db_id;
                }
                m_market_depth_list_.market_depth_.push_back(market_depth);

                if (mr_config_.m_market_depth_http_update_publish_policy_ == PublishPolicy::POST) {
                    auto db_id = m_market_depth_codec_.get_db_id_from_root_model_obj(market_depth);
                    if (db_id == -1) {
                        if(!m_md_http_client_.value().create_client(market_depth)) {
                            LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to create client market_depth;;; id: {}, "
                                                              "symbol: {}", market_depth.id_, market_depth.symbol_);
                        }
                        std::string md_key;
                        MobileBookKeyHandler::get_key_out(market_depth, md_key);
                        m_market_depth_codec_.m_root_model_key_to_db_id[md_key] = db_id;
                    } else {
                        market_depth.id_ = db_id;
                        if(!m_md_http_client_.value().patch_client(market_depth)) {
                            LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to patch client market_depth;;; id: {}, "
                                                              "symbol: {}", market_depth.id_, market_depth.symbol_);
                        }
                    }
                }

                if (market_depth.position_ == 0) {
                    TopOfBook top_of_book;
                    top_of_book.id_ = market_depth.id_;
                    top_of_book.symbol_ = market_depth.symbol_;
                    top_of_book.last_update_date_time_ = market_depth.exch_time_;
                    top_of_book.is_last_update_date_time_set_ = true;

                    auto& quote = (market_depth.side_ == "BID") ? top_of_book.bid_quote_ : top_of_book.ask_quote_;

                    quote.px_ = market_depth.px_;
                    quote.qty_ = market_depth.qty_;
                    quote.is_qty_set_ = true;
                    quote.is_px_set_ = true;
                    quote.is_last_update_date_time_set_ = true;
                    quote.last_update_date_time_ = market_depth.exch_time_;

                    if (market_depth.side_ == "BID") {
                        top_of_book.is_bid_quote_set_ = true;
                    } else {
                        top_of_book.is_ask_quote_set_ = true;
                    }
                    top_of_book.is_market_barter_volume_set_ = false;

                    if (mr_config_.m_top_of_book_db_update_publish_policy_ == PublishPolicy::POST) {
                        std::string tob_key;
                        MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
                        auto found = m_top_of_book_codec_.m_root_model_key_to_db_id.find(tob_key);
                        if (found == m_top_of_book_codec_.m_root_model_key_to_db_id.end()) {
                            top_of_book.id_ = m_top_of_book_codec_.get_next_insert_id();
                            m_top_of_book_codec_.insert(top_of_book);
                            m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
                        } else {
                            top_of_book.id_ = found->second;
                            m_top_of_book_codec_.patch(top_of_book);
                        }
                    }

                    if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::POST) {
                        auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
                        if (db_id == -1) {
                            if(!m_tob_web_client_.value().create_client(top_of_book)) {
                                LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to create client top_of_book;;; id: {}, "
                                                                  "symbol: {}", top_of_book.id_, top_of_book.symbol_);
                            }
                            std::string tob_key;
                            MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
                            m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
                        } else {
                            top_of_book.id_ = db_id;
                            if(!m_tob_web_client_.value().patch_client(top_of_book)) {
                                LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to patch client top_of_book;;; id: {}, "
                                                                  "symbol: {}", top_of_book.id_, top_of_book.symbol_);
                            }
                        }
                        // if (m_top_of_book_codec_.m_root_model_key_to_db_id.find())
                    }

                    if (mr_config_.m_top_of_book_ws_update_publish_policy_ == PublishPolicy::POST) {
                        auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
                        top_of_book.id_ = db_id;
                        top_of_book.market_barter_volume_.clear();
                        m_top_of_book_codec_.get_data_by_id_from_collection(top_of_book, db_id);
                        boost::json::object tob_json;
                        if (MobileBookObjectToJson::object_to_json(top_of_book, tob_json)) {
                            m_combined_server_->publish_to_route(mr_config_.m_top_of_book_ws_route_,
                                boost::json::serialize(tob_json));
                        } else {
                            LOG_ERROR_IMPL(GetCppAppLogger(), "Failed to serialize top_of_book to json;;; id: {}, "
                                                              "symbol: {}, ", top_of_book.id_, top_of_book.symbol_);
                        }
                    }
                }
            }

            if (mr_config_.m_market_depth_ws_update_publish_policy_ == PublishPolicy::POST) {
                boost::json::object md_json;
                if (MobileBookObjectToJson::object_to_json(m_market_depth_list_, md_json)) {
                    m_combined_server_->publish_to_route(mr_config_.m_market_depth_ws_route_,
                        boost::json::serialize(md_json["market_depth"].get_array()));
                } else {
                    // TODO: fix error
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Failed to serialize market_depth to json;;; id: {}, symbol: {}, "
                                                      "", m_market_depth.id_, m_market_depth.symbol_);
                }
                m_market_depth_list_.market_depth_.clear();
            }
        }
    }
}

void MobileBookPublisher::last_barter_consumer() {
    LastBarterQueueElement last_barter_queue_element;
    while (keepRunning) {
        auto status = m_last_barter_monitor_.pop(last_barter_queue_element, std::chrono::milliseconds(100));
        if (status == FluxCppCore::QueueStatus::DATA_CONSUMED) {
            if (last_barter_queue_element.symbol_n_exch_id_.symbol_!= mr_config_.m_leg_1_symbol_ &&
                last_barter_queue_element.symbol_n_exch_id_.symbol_!= mr_config_.m_leg_2_symbol_) {
                continue;
            }
            LastBarter last_barter{};
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::POST) {
                switch (mr_config_.m_market_depth_level_) {
                    case 1: {
                        auto shm_cache = static_cast<ShmSymbolCache<1>*>(m_shm_symbol_cache_);
                        auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<1>>*>(m_shm_manager_);
                        if (last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
                            ++shm_cache->m_leg_1_data_shm_cache_.update_counter;
                            update_last_barter_cache(last_barter_queue_element, shm_cache->m_leg_1_data_shm_cache_);
                        }
                        if (last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
                            ++shm_cache->m_leg_2_data_shm_cache_.update_counter;
                            update_last_barter_cache(last_barter_queue_element, shm_cache->m_leg_2_data_shm_cache_);
                        }
                        auto result = shm_manager->write_to_shared_memory(*shm_cache);
                        log_lt(last_barter_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
                        break;
                    } case 5: {
                        auto shm_cache = static_cast<ShmSymbolCache<5>*>(m_shm_symbol_cache_);
                        auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<5>>*>(m_shm_manager_);
                        if (last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
                            ++shm_cache->m_leg_1_data_shm_cache_.update_counter;
                            update_last_barter_cache(last_barter_queue_element, shm_cache->m_leg_1_data_shm_cache_);
                        }
                        if (last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
                            ++shm_cache->m_leg_2_data_shm_cache_.update_counter;
                            update_last_barter_cache(last_barter_queue_element, shm_cache->m_leg_2_data_shm_cache_);
                        }
                        auto result = shm_manager->write_to_shared_memory(*shm_cache);
                        log_lt(last_barter_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
                        break;
                    } case 10: {
                        auto shm_cache = static_cast<ShmSymbolCache<10>*>(m_shm_symbol_cache_);
                        auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<10>>*>(m_shm_manager_);
                        if (last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
                            ++shm_cache->m_leg_1_data_shm_cache_.update_counter;
                            update_last_barter_cache(last_barter_queue_element, shm_cache->m_leg_1_data_shm_cache_);
                        }
                        if (last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
                            ++shm_cache->m_leg_2_data_shm_cache_.update_counter;
                            update_last_barter_cache(last_barter_queue_element, shm_cache->m_leg_2_data_shm_cache_);
                        }
                        auto result = shm_manager->write_to_shared_memory(*shm_cache);
                        log_lt(last_barter_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
                        break;
                    } case 15: {
                        auto shm_cache = static_cast<ShmSymbolCache<15>*>(m_shm_symbol_cache_);
                        auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<15>>*>(m_shm_manager_);
                        if (last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
                            ++shm_cache->m_leg_1_data_shm_cache_.update_counter;
                            update_last_barter_cache(last_barter_queue_element, shm_cache->m_leg_1_data_shm_cache_);
                        }
                        if (last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
                            ++shm_cache->m_leg_2_data_shm_cache_.update_counter;
                            update_last_barter_cache(last_barter_queue_element, shm_cache->m_leg_2_data_shm_cache_);
                        }
                        auto result = shm_manager->write_to_shared_memory(*shm_cache);
                        log_lt(last_barter_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
                        break;
                    } case 20: {
                        auto shm_cache = static_cast<ShmSymbolCache<20>*>(m_shm_symbol_cache_);
                        auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<20>>*>(m_shm_manager_);
                        if (last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
                            ++shm_cache->m_leg_1_data_shm_cache_.update_counter;
                            update_last_barter_cache(last_barter_queue_element, shm_cache->m_leg_1_data_shm_cache_);
                        }
                        if (last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
                            ++shm_cache->m_leg_2_data_shm_cache_.update_counter;
                            update_last_barter_cache(last_barter_queue_element, shm_cache->m_leg_2_data_shm_cache_);
                        }
                        auto result = shm_manager->write_to_shared_memory(*shm_cache);
                        log_lt(last_barter_queue_element, result ? "successfully written to SHM" : "Failed to write to SHM");
                        break;
                    }
                    default: {
                        LOG_ERROR_IMPL(GetCppAppLogger(), "Unsupported market depth level: {};;; supported levels are: "
                                              "1, 5, 10, 15, 20", mr_config_.m_market_depth_level_);
                        break;
                    }
                }
            }

            last_barter.id_ = last_barter_queue_element.id_;
            last_barter.symbol_n_exch_id_.symbol_ = last_barter_queue_element.symbol_n_exch_id_.symbol_;
            last_barter.symbol_n_exch_id_.exch_id_ = last_barter_queue_element.symbol_n_exch_id_.exch_id_;
            last_barter.exch_time_ = last_barter_queue_element.exch_time_;
            last_barter.arrival_time_ = last_barter_queue_element.arrival_time_;
            last_barter.px_ = last_barter_queue_element.px_;
            last_barter.qty_ = last_barter_queue_element.qty_;
            if (last_barter_queue_element.is_premium_set_) {
                last_barter.premium_ = last_barter_queue_element.premium_;
                last_barter.is_premium_set_ = true;
            }

            if (last_barter_queue_element.is_market_barter_volume_set_) {
                last_barter.market_barter_volume_.id_ = last_barter_queue_element.market_barter_volume_.id_;

                if (last_barter_queue_element.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_) {
                    last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_ =
                        last_barter_queue_element.market_barter_volume_.participation_period_last_barter_qty_sum_;
                    last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = true;
                }

                if (last_barter_queue_element.market_barter_volume_.is_applicable_period_seconds_set_) {
                    last_barter.market_barter_volume_.applicable_period_seconds_ =
                        last_barter_queue_element.market_barter_volume_.applicable_period_seconds_;
                    last_barter.market_barter_volume_.is_applicable_period_seconds_set_ = true;
                }
                last_barter.is_market_barter_volume_set_ = true;
            }

            if (mr_config_.m_last_barter_db_update_publish_policy_ == PublishPolicy::POST) {
                last_barter.id_ = m_last_barter_codec_.get_next_insert_id();
                m_last_barter_codec_.insert(last_barter);
            }

            if (mr_config_.m_last_barter_http_update_publish_policy_ == PublishPolicy::POST) {
                if (!m_lt_web_client_.value().create_client(last_barter)) {
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to create client last_barter;;; id: {}, symbol: {}",
                        last_barter.id_, last_barter.symbol_n_exch_id_.symbol_);
                }
            }

            if (mr_config_.m_last_barter_ws_update_publish_policy_ == PublishPolicy::POST) {
                boost::json::object lt_json;
                if (MobileBookObjectToJson::object_to_json(last_barter, lt_json)) {
                    m_combined_server_->publish_to_route(mr_config_.m_last_barter_ws_route_,
                        boost::json::serialize(lt_json));
                } else {
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Failed to serialize last_barter to json;;; id: {}, symbol: {}",
                        last_barter.id_, last_barter.symbol_n_exch_id_.symbol_);
                }
            }

            auto time = FluxCppCore::get_local_time_microseconds<int64_t>();
            TopOfBook top_of_book;
            top_of_book.id_ = last_barter.id_;
            top_of_book.symbol_ = last_barter.symbol_n_exch_id_.symbol_;
            top_of_book.last_update_date_time_ = last_barter.exch_time_;
            top_of_book.is_last_update_date_time_set_ = true;
            top_of_book.last_barter_.px_ = last_barter.px_;
            top_of_book.last_barter_.qty_ = last_barter.qty_;
            top_of_book.last_barter_.last_update_date_time_ = last_barter.exch_time_;
            top_of_book.last_barter_.is_last_update_date_time_set_ = true;
            top_of_book.is_last_barter_set_ = true;
            top_of_book.last_barter_.is_px_set_ = true;
            top_of_book.last_barter_.is_qty_set_ = true;
            if (last_barter_queue_element.is_premium_set_) {
                top_of_book.last_barter_.premium_ = last_barter.premium_;
                top_of_book.last_barter_.is_premium_set_ = true;
            }

            if (last_barter_queue_element.is_market_barter_volume_set_) {
                top_of_book.market_barter_volume_.push_back(last_barter.market_barter_volume_);
                top_of_book.is_market_barter_volume_set_ = true;
            }

            if (mr_config_.m_top_of_book_db_update_publish_policy_ == PublishPolicy::POST) {
                std::string tob_key;
                MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
                auto found = m_top_of_book_codec_.m_root_model_key_to_db_id.find(tob_key);
                if (found == m_top_of_book_codec_.m_root_model_key_to_db_id.end()) {
                    top_of_book.id_ = m_top_of_book_codec_.get_next_insert_id();
                    m_top_of_book_codec_.insert(top_of_book);
                    m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
                } else {
                    top_of_book.id_ = found->second;
                    m_top_of_book_codec_.patch(top_of_book);
                }
            }

            if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::POST) {
                auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
                if (db_id == -1) {
                    if (!m_tob_web_client_.value().create_client(top_of_book)) {
                        LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to create client top_of_book;;; id: {}, symbol: {}",
                            top_of_book.id_, top_of_book.symbol_);
                    }
                    std::string tob_key;
                    MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
                    m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
                } else {
                    top_of_book.id_ = db_id;
                    if(!m_tob_web_client_.value().patch_client(top_of_book)) {
                        LOG_ERROR_IMPL(GetCppAppLogger(), "Fliled to patch client top_of_book;;; id: {}, symbol: {}",
                            top_of_book.id_, top_of_book.symbol_);
                    }
                }
                // if (m_top_of_book_codec_.m_root_model_key_to_db_id.find())
            }

            if (mr_config_.m_top_of_book_ws_update_publish_policy_ == PublishPolicy::POST) {
                auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
                top_of_book.market_barter_volume_.clear();
                top_of_book.id_ = db_id;
                m_top_of_book_codec_.get_data_by_id_from_collection(top_of_book, db_id);
                boost::json::object tob_json;
                MobileBookObjectToJson::object_to_json(top_of_book, tob_json);
                m_combined_server_->publish_to_route(mr_config_.m_top_of_book_ws_route_,
                    boost::json::serialize(tob_json));
            }
        }
    }
}

void MobileBookPublisher::start_monitor_threads() {
    m_market_depth_monitor_thread_ = std::jthread([this]() { market_depth_consumer(); });
	m_last_barter_monitor_thread_ = std::jthread([this]() { last_barter_consumer(); });
}

void MobileBookPublisher::populate_market_depth_queue_element(const MarketDepthQueueElement& kr_market_depth_queue_element,
    MarketDepth& r_market_depth) const {

    const auto current_time = FluxCppCore::get_local_time_microseconds<int64_t>();
    r_market_depth.id_ = kr_market_depth_queue_element.id_;
    r_market_depth.symbol_ = kr_market_depth_queue_element.symbol_;
    r_market_depth.exch_time_ = current_time;
    r_market_depth.arrival_time_ = current_time;

    if (kr_market_depth_queue_element.is_px_set_) {
        r_market_depth.px_ = kr_market_depth_queue_element.px_;
        r_market_depth.is_px_set_ = true;
    }

    if (kr_market_depth_queue_element.is_qty_set_) {
        r_market_depth.qty_ = kr_market_depth_queue_element.qty_;
        r_market_depth.is_qty_set_ = true;
    }
    r_market_depth.position_ = kr_market_depth_queue_element.position_;

    if (kr_market_depth_queue_element.is_market_maker_set_) {
        r_market_depth.market_maker_ = kr_market_depth_queue_element.market_maker_;
        r_market_depth.is_market_maker_set_ = true;
    }

    if (kr_market_depth_queue_element.is_is_smart_depth_set_) {
        r_market_depth.is_smart_depth_ = kr_market_depth_queue_element.is_smart_depth_;
        r_market_depth.is_is_smart_depth_set_ = true;
    }

    if (kr_market_depth_queue_element.is_cumulative_notional_set_) {
        r_market_depth.cumulative_notional_ = kr_market_depth_queue_element.cumulative_notional_;
        r_market_depth.is_cumulative_notional_set_ = true;
    }

    if (kr_market_depth_queue_element.is_cumulative_qty_set_) {
        r_market_depth.cumulative_qty_ = kr_market_depth_queue_element.cumulative_qty_;
        r_market_depth.is_cumulative_qty_set_ = true;
    }

    if (kr_market_depth_queue_element.is_cumulative_avg_px_set_) {
        r_market_depth.cumulative_avg_px_ = kr_market_depth_queue_element.cumulative_avg_px_;
        r_market_depth.is_cumulative_avg_px_set_ = true;
    }

}