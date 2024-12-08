#include "mobile_book_publisher.h"

#include "../include/md_utility_functions.h"

void MobileBookPublisher::cleanup() {
    m_shutdown_flag_ = true;
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
	        std::cerr << "Invalid market depth level: " << mr_config_.m_market_depth_level_ << std::endl;
            break;
	    }
	}
    if (m_top_of_book_web_socket_server_) {
    	m_top_of_book_web_socket_server_.value().clean_ws();
    }
    if (m_market_depth_web_socket_server_) {
        m_market_depth_web_socket_server_.value().clean_ws();
    }
    if (m_last_barter_web_socket_server_) {
        m_last_barter_web_socket_server_.value().clean_ws();
    }
}

void MobileBookPublisher::process_market_depth(MarketDepthQueueElement& r_market_depth_queue_element) {
    if (r_market_depth_queue_element.symbol_ != mr_config_.m_leg_1_symbol_ &&
        r_market_depth_queue_element.symbol_ != mr_config_.m_leg_2_symbol_) {
        return;
    }

    // Update symbol-specific caches
    auto update_symbol_cache = [&](auto& symbol_cache) {
        ++symbol_cache.update_counter;
        update_market_depth_cache(r_market_depth_queue_element, symbol_cache);
        mobile_book_handler::compute_cumulative_fields_from_market_depth_elements(
            symbol_cache, r_market_depth_queue_element
        );
    };

    MarketDepth market_depth{};
    populate_market_depth(r_market_depth_queue_element, market_depth);

    switch (mr_config_.m_market_depth_level_) {
        case 1: {
            auto shm_cache = static_cast<ShmSymbolCache<1>*>(m_shm_symbol_cache_);
            if (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) {
                update_symbol_cache(shm_cache->m_leg_1_data_shm_cache_);
            }
            if (market_depth.symbol_ == mr_config_.m_leg_2_symbol_) {
                update_symbol_cache(shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<1>>*>(m_shm_manager_);
                shm_manager->write_to_shared_memory(*shm_cache);
            }
            break;
        }
        case 5: {
            auto shm_cache = static_cast<ShmSymbolCache<5>*>(m_shm_symbol_cache_);
            if (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) {
                update_symbol_cache(shm_cache->m_leg_1_data_shm_cache_);
            }
            if (market_depth.symbol_ == mr_config_.m_leg_2_symbol_) {
                update_symbol_cache(shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<5>>*>(m_shm_manager_);
                shm_manager->write_to_shared_memory(*shm_cache);
            }
            break;
        }
        case 10: {
            auto shm_cache = static_cast<ShmSymbolCache<10>*>(m_shm_symbol_cache_);
            if (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) {
                update_symbol_cache(shm_cache->m_leg_1_data_shm_cache_);
            }
            if (market_depth.symbol_ == mr_config_.m_leg_2_symbol_) {
                update_symbol_cache(shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<10>>*>(m_shm_manager_);
                shm_manager->write_to_shared_memory(*shm_cache);
            }
            break;
        }
        case 15: {
            auto shm_cache = static_cast<ShmSymbolCache<15>*>(m_shm_symbol_cache_);
            if (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) {
                update_symbol_cache(shm_cache->m_leg_1_data_shm_cache_);
            }
            if (market_depth.symbol_ == mr_config_.m_leg_2_symbol_) {
                update_symbol_cache(shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<15>>*>(m_shm_manager_);
                shm_manager->write_to_shared_memory(*shm_cache);
            }
            break;
        }
        case 20: {
            auto shm_cache = static_cast<ShmSymbolCache<20>*>(m_shm_symbol_cache_);
            if (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) {
                update_symbol_cache(shm_cache->m_leg_1_data_shm_cache_);
            }
            if (market_depth.symbol_ == mr_config_.m_leg_2_symbol_) {
                update_symbol_cache(shm_cache->m_leg_2_data_shm_cache_);
            }
            if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
                auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<20>>*>(m_shm_manager_);
                shm_manager->write_to_shared_memory(*shm_cache);
            }
            break;
        }
    }

    // Update market depth database if PRE policy
    if (mr_config_.m_market_depth_db_update_publish_policy_ == PublishPolicy::PRE) {
        m_market_depth_codec_.insert_or_update(market_depth);
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
            m_top_of_book_codec_.insert_or_update(top_of_book);
        }

        if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::PRE) {
            auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
            if (db_id == -1) {
                assert(m_tob_web_client_.value().create_client(top_of_book));
                std::string tob_key;
                MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
                m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
            } else {
                top_of_book.id_ = db_id;
                assert(m_tob_web_client_.value().patch_client(top_of_book));
            }
            // if (m_top_of_book_codec_.m_root_model_key_to_db_id.find())
        }

        if (mr_config_.m_market_depth_db_update_publish_policy_ == PublishPolicy::PRE) {
            auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
            top_of_book.id_ = db_id;
            m_top_of_book_codec_.get_data_by_id_from_collection(top_of_book, db_id);
            m_top_of_book_web_socket_server_.value().publish(top_of_book);
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
                    ((r_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_1_data_shm_cache_.bid_market_depths_
                        : shm_cache->m_leg_1_data_shm_cache_.ask_market_depths_)
                : ((r_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_2_data_shm_cache_.bid_market_depths_
                    : shm_cache->m_leg_2_data_shm_cache_.ask_market_depths_);

                for (size_t i = r_market_depth_queue_element.position_; i < md_array.size(); ++i) {
                    if (!md_array[i].is_px_set_) break;
                    m_market_depth_queue_element_list_.push_back(md_array[i]);
                }
                m_market_depth_monitor_.push(m_market_depth_queue_element_list_);
                m_market_depth_queue_element_list_.clear();
                break;
            } case 5: {
                auto shm_cache = static_cast<ShmSymbolCache<5>*>(m_shm_symbol_cache_);
                const auto& md_array = (market_depth.symbol_ == mr_config_.m_leg_1_symbol_) ?
                    ((r_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_1_data_shm_cache_.bid_market_depths_
                        : shm_cache->m_leg_1_data_shm_cache_.ask_market_depths_)
                : ((r_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_2_data_shm_cache_.bid_market_depths_
                    : shm_cache->m_leg_2_data_shm_cache_.ask_market_depths_);

                for (size_t i = r_market_depth_queue_element.position_; i < md_array.size(); ++i) {
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
                    ((r_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_1_data_shm_cache_.bid_market_depths_
                        : shm_cache->m_leg_1_data_shm_cache_.ask_market_depths_)
                : ((r_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_2_data_shm_cache_.bid_market_depths_
                    : shm_cache->m_leg_2_data_shm_cache_.ask_market_depths_);

                for (size_t i = r_market_depth_queue_element.position_; i < md_array.size(); ++i) {
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
                    ((r_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_1_data_shm_cache_.bid_market_depths_
                        : shm_cache->m_leg_1_data_shm_cache_.ask_market_depths_)
                : ((r_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_2_data_shm_cache_.bid_market_depths_
                    : shm_cache->m_leg_2_data_shm_cache_.ask_market_depths_);

                for (size_t i = r_market_depth_queue_element.position_; i < md_array.size(); ++i) {
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
                    ((r_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_1_data_shm_cache_.bid_market_depths_
                        : shm_cache->m_leg_1_data_shm_cache_.ask_market_depths_)
                : ((r_market_depth_queue_element.side_ == 'B') ? shm_cache->m_leg_2_data_shm_cache_.bid_market_depths_
                    : shm_cache->m_leg_2_data_shm_cache_.ask_market_depths_);

                for (size_t i = r_market_depth_queue_element.position_; i < md_array.size(); ++i) {
                    if (!md_array[i].is_px_set_) break;
                    m_market_depth_queue_element_list_.push_back(md_array[i]);
                }
                m_market_depth_monitor_.push(m_market_depth_queue_element_list_);
                m_market_depth_queue_element_list_.clear();
                break;
            }
        }
	}
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
                shm_manager->write_to_shared_memory(*shm_cache);
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
                shm_manager->write_to_shared_memory(*shm_cache);
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
                shm_manager->write_to_shared_memory(*shm_cache);
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
                shm_manager->write_to_shared_memory(*shm_cache);
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
                shm_manager->write_to_shared_memory(*shm_cache);
            }
            break;
        }
    }

    if (mr_config_.m_last_barter_db_update_publish_policy_ == PublishPolicy::PRE) {
        m_last_barter_codec_.insert(last_barter);
    }

    if (mr_config_.m_last_barter_ws_update_publish_policy_ == PublishPolicy::PRE) {
        m_last_barter_web_socket_server_.value().publish(last_barter);
    }

    if (mr_config_.m_last_barter_http_update_publish_policy_ == PublishPolicy::PRE) {
        assert(m_lt_web_client_.value().create_client(last_barter));
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
    }

    if (mr_config_.m_top_of_book_db_update_publish_policy_  == PublishPolicy::PRE) {
        m_top_of_book_codec_.insert_or_update(top_of_book);
    }

    if (mr_config_.m_top_of_book_ws_update_publish_policy_ == PublishPolicy::PRE) {
        auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
        top_of_book.id_ = db_id;
        m_top_of_book_codec_.get_data_by_id_from_collection(top_of_book, db_id);
        m_top_of_book_web_socket_server_.value().publish(top_of_book);
    }

    if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::PRE) {
        auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
        if (db_id == -1) {
            assert(m_tob_web_client_.value().create_client(top_of_book));
            std::string tob_key;
            MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
            m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
        } else {
            top_of_book.id_ = db_id;
            assert(m_tob_web_client_.value().patch_client(top_of_book));
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

template<size_t N>
void MobileBookPublisher::update_market_depth_cache(const MarketDepthQueueElement& kr_market_depth_queue_element,
	MDContainer<N>& r_mobile_book_cache_out) {

    if (kr_market_depth_queue_element.side_ == 'B') {
        r_mobile_book_cache_out.bid_market_depths_[kr_market_depth_queue_element.position_] = kr_market_depth_queue_element;
    }

    if (kr_market_depth_queue_element.side_ == 'A') {
        r_mobile_book_cache_out.ask_market_depths_[kr_market_depth_queue_element.position_] = kr_market_depth_queue_element;
    }

    if (kr_market_depth_queue_element.position_ == 0) {
        r_mobile_book_cache_out.top_of_book_.id_ = kr_market_depth_queue_element.id_;
        FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.symbol_,
            kr_market_depth_queue_element.symbol_, sizeof(r_mobile_book_cache_out.top_of_book_.symbol_));
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
	MDContainer<N>& r_mobile_book_cache_out) {
	// LastBarter
		r_mobile_book_cache_out.last_barter_ = kr_last_barter_queue_element;

		// TopOfBook
		FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.symbol_,
			kr_last_barter_queue_element.symbol_n_exch_id_.symbol_, sizeof(r_mobile_book_cache_out.top_of_book_.symbol_));
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
}

void MobileBookPublisher::populate_market_depth(
    const MarketDepthQueueElement& kr_market_depth_queue_element, MarketDepth& r_market_depth) {

    r_market_depth.id_ = kr_market_depth_queue_element.id_;
    r_market_depth.symbol_ = kr_market_depth_queue_element.symbol_;
    r_market_depth.exch_time_  = kr_market_depth_queue_element.exch_time_;
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
        std::cout << "Websocket starting websocket\n";
        m_market_depth_web_socket_server_.emplace(m_market_depth_list_, m_market_depth_codec_, mobile_book_handler::host,
            mr_config_.m_market_depth_ws_port_,
            std::chrono::seconds(mobile_book_handler::connection_timeout));
    }

    if (mr_config_.m_last_barter_ws_update_publish_policy_ != PublishPolicy::OFF) {
        m_last_barter_web_socket_server_.emplace(m_last_barter_, m_last_barter_codec_, mobile_book_handler::host,
            mr_config_.m_last_barter_ws_port_,
            std::chrono::seconds(mobile_book_handler::connection_timeout));
    }

    if (mr_config_.m_top_of_book_ws_update_publish_policy_ != PublishPolicy::OFF) {
        std::cout << "Websocket starting websocket\n";
        m_top_of_book_web_socket_server_.emplace(m_top_of_book_, m_top_of_book_codec_, mobile_book_handler::host,
            mr_config_.m_top_of_book_ws_port_,
            std::chrono::seconds(mobile_book_handler::connection_timeout));
    }
}

void MobileBookPublisher::market_depth_consumer() {
    std::vector<MarketDepthQueueElement> market_depth_queue_element_list;
    while (!m_shutdown_flag_) {
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
                            shm_manger->write_to_shared_memory(*shm_cache);
                            break;
                        }
                        case 5: {
                            auto shm_cache = static_cast<ShmSymbolCache<5>*>(m_shm_symbol_cache_);
                            auto shm_manger = static_cast<SharedMemoryManager<ShmSymbolCache<5>>*>(m_shm_manager_);
                            shm_manger->write_to_shared_memory(*shm_cache);
                            break;
                        }
                        case 10: {
                            auto shm_cache = static_cast<ShmSymbolCache<10>*>(m_shm_symbol_cache_);
                            auto shm_manger = static_cast<SharedMemoryManager<ShmSymbolCache<10>>*>(m_shm_manager_);
                            shm_manger->write_to_shared_memory(*shm_cache);
                            break;
                        } case 15: {
                            auto shm_cache = static_cast<ShmSymbolCache<15>*>(m_shm_symbol_cache_);
                            auto shm_manger = static_cast<SharedMemoryManager<ShmSymbolCache<15>>*>(m_shm_manager_);
                            shm_manger->write_to_shared_memory(*shm_cache);
                            break;
                        }
                        case 20: {
                            auto shm_cache = static_cast<ShmSymbolCache<20>*>(m_shm_symbol_cache_);
                            auto shm_manger = static_cast<SharedMemoryManager<ShmSymbolCache<20>>*>(m_shm_manager_);
                            shm_manger->write_to_shared_memory(*shm_cache);
                            break;
                        }
                    }
                }
                populate_market_depth(market_depth_queue_element, market_depth);
                m_market_depth_list_.market_depth_.push_back(market_depth);

                if (mr_config_.m_market_depth_db_update_publish_policy_ == PublishPolicy::POST) {
                    m_market_depth_codec_.insert_or_update(market_depth);
                }

                if (mr_config_.m_market_depth_http_update_publish_policy_ == PublishPolicy::POST) {
                    auto db_id = m_market_depth_codec_.get_db_id_from_root_model_obj(market_depth);
                    if (db_id == -1) {
                        assert(m_md_http_client_.value().create_client(market_depth));
                        std::string md_key;
                        MobileBookKeyHandler::get_key_out(market_depth, md_key);
                        m_market_depth_codec_.m_root_model_key_to_db_id[md_key] = db_id;
                    } else {
                        market_depth.id_ = db_id;
                        assert(m_md_http_client_.value().patch_client(market_depth));
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

                    if (mr_config_.m_top_of_book_db_update_publish_policy_ == PublishPolicy::POST) {
                        m_top_of_book_codec_.insert_or_update(top_of_book);
                    }

                    if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::POST) {
                        auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
                        if (db_id == -1) {
                            assert(m_tob_web_client_.value().create_client(top_of_book));
                            std::string tob_key;
                            MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
                            m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
                        } else {
                            top_of_book.id_ = db_id;
                            assert(m_tob_web_client_.value().patch_client(top_of_book));
                        }
                        // if (m_top_of_book_codec_.m_root_model_key_to_db_id.find())
                    }

                    if (mr_config_.m_market_depth_db_update_publish_policy_ == PublishPolicy::POST) {
                        auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
                        top_of_book.id_ = db_id;
                        m_top_of_book_codec_.get_data_by_id_from_collection(top_of_book, db_id);
                        m_top_of_book_web_socket_server_.value().publish(top_of_book);
                    }
                }
            }

            if (mr_config_.m_market_depth_ws_update_publish_policy_ == PublishPolicy::POST) {
                m_market_depth_web_socket_server_.value().publish(m_market_depth_list_);
                m_market_depth_list_.market_depth_.clear();
            }
        }
    }
}

void MobileBookPublisher::last_barter_consumer() {
    LastBarterQueueElement last_barter_queue_element;
    while (!m_shutdown_flag_) {
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
                        shm_manager->write_to_shared_memory(*shm_cache);
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
                        shm_manager->write_to_shared_memory(*shm_cache);
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
                        shm_manager->write_to_shared_memory(*shm_cache);
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
                        shm_manager->write_to_shared_memory(*shm_cache);
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
                        shm_manager->write_to_shared_memory(*shm_cache);
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
                m_last_barter_codec_.insert(last_barter);
            }

            if (mr_config_.m_last_barter_http_update_publish_policy_ == PublishPolicy::PRE) {
                assert(m_lt_web_client_.value().create_client(last_barter));
            }

            if (mr_config_.m_last_barter_ws_update_publish_policy_ == PublishPolicy::POST) {
                m_last_barter_web_socket_server_.value().publish(last_barter);
            }

            TopOfBook top_of_book;
            top_of_book.id_ = last_barter.id_;
            top_of_book.symbol_ = last_barter_queue_element.symbol_n_exch_id_.symbol_;
            top_of_book.last_update_date_time_ = last_barter_queue_element.exch_time_;
            top_of_book.is_last_update_date_time_set_ = true;
            top_of_book.last_barter_.px_ = last_barter.px_;
            top_of_book.last_barter_.qty_ = last_barter.qty_;
            top_of_book.last_barter_.last_update_date_time_ = last_barter_queue_element.exch_time_;
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
                m_top_of_book_codec_.insert_or_update(top_of_book);
            }

            if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::POST) {
                auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
                if (db_id == -1) {
                    assert(m_tob_web_client_.value().create_client(top_of_book));
                    std::string tob_key;
                    MobileBookKeyHandler::get_key_out(top_of_book, tob_key);
                    m_top_of_book_codec_.m_root_model_key_to_db_id[tob_key] = top_of_book.id_;
                } else {
                    top_of_book.id_ = db_id;
                    assert(m_tob_web_client_.value().patch_client(top_of_book));
                }
                // if (m_top_of_book_codec_.m_root_model_key_to_db_id.find())
            }

            if (mr_config_.m_top_of_book_ws_update_publish_policy_ == PublishPolicy::POST) {
                auto db_id = m_top_of_book_codec_.get_db_id_from_root_model_obj(top_of_book);
                top_of_book.id_ = db_id;
                m_top_of_book_codec_.get_data_by_id_from_collection(top_of_book, db_id);
                m_top_of_book_web_socket_server_.value().publish(top_of_book);
            }
        }
    }
}

void MobileBookPublisher::start_monitor_threads() {
    m_market_depth_monitor_thread_ = std::jthread([this]() { market_depth_consumer(); });
	m_last_barter_monitor_thread_ = std::jthread([this]() { last_barter_consumer(); });
}

void MobileBookPublisher::populate_market_depth_queue_element(const MarketDepthQueueElement& kr_market_depth_queue_element,
    MarketDepth& r_market_depth) {

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