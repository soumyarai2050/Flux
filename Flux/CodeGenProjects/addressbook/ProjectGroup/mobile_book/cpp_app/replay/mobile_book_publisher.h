#pragma once

#include <optional>
#include <thread>
#include <atomic>

#include <yaml-cpp/yaml.h>

#include "mobile_book_constants.h"
#include "mongo_db_handler.h"
#include "mongo_db_codec.h"
#include "shared_memory_manager.h"
#include "../include/config_parser.h"
#include "mobile_book_web_socket_server.h"
#include "queue_handler.h"
#include "mobile_book_service_shared_data_structure.h"
#include "../include/md_utility_functions.h"
#include "../include/shm_symbol_cache.h"
#include "base_web_client.h"

class MobileBookPublisher {
public:
    explicit MobileBookPublisher(Config& config) : mr_config_(config),
    m_sp_mongo_db_handler_(std::make_shared<FluxCppCore::MongoDBHandler>(
        mr_config_.m_mongodb_uri_, mr_config_.m_db_name_)), m_market_depth_codec_(m_sp_mongo_db_handler_),
    m_last_barter_codec_(m_sp_mongo_db_handler_), m_top_of_book_codec_(m_sp_mongo_db_handler_),
    m_raw_market_depth_history_codec_(m_sp_mongo_db_handler_), m_raw_last_barter_history_codec_(m_sp_mongo_db_handler_) {

		initialize_shm();
        m_raw_last_barter_history_codec_.get_all_data_from_collection(m_raw_last_barter_history_list_);
        m_raw_market_depth_history_codec_.get_all_data_from_collection(m_raw_market_depth_history_list_);
        update_market_depth_db_cache();
        update_top_of_book_db_cache();
    	initialize_webclient();
        initialize_websocket_servers();
        start_monitor_threads();
    }

    void cleanup();

    void process_market_depth(const MarketDepthQueueElement& r_market_depth_queue_element);

    void process_last_barter(const LastBarterQueueElement& kr_last_barter_queue_element);

	void init_shared_memory() {
		switch (mr_config_.m_market_depth_level_) {
			case 1: {
				auto shm_cache = static_cast<ShmSymbolCache<1>*>(m_shm_symbol_cache_);
				auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<1>>*>(m_shm_manager_);
				shm_cache->m_leg_1_data_shm_cache_.update_counter = 0;
				shm_cache->m_leg_2_data_shm_cache_.update_counter = 0;
				FluxCppCore::StringUtil::setString(shm_cache->m_leg_1_data_shm_cache_.symbol_,
					mr_config_.m_leg_1_symbol_);
				FluxCppCore::StringUtil::setString(shm_cache->m_leg_2_data_shm_cache_.symbol_,
		            mr_config_.m_leg_2_symbol_);
				shm_manager->write_to_shared_memory(*shm_cache);
				LOG_INFO_IMPL(GetCppAppLogger(), "{}", mobile_book_handler::shm_snapshot(*shm_cache));
				break;
			}
			case 5: {
				auto shm_cache = static_cast<ShmSymbolCache<5>*>(m_shm_symbol_cache_);
				auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<5>>*>(m_shm_manager_);
				shm_cache->m_leg_1_data_shm_cache_.update_counter = 0;
				shm_cache->m_leg_2_data_shm_cache_.update_counter = 0;
				FluxCppCore::StringUtil::setString(shm_cache->m_leg_1_data_shm_cache_.symbol_,
					mr_config_.m_leg_1_symbol_);
				FluxCppCore::StringUtil::setString(shm_cache->m_leg_2_data_shm_cache_.symbol_,
		            mr_config_.m_leg_2_symbol_);
				shm_manager->write_to_shared_memory(*shm_cache);
				LOG_INFO_IMPL(GetCppAppLogger(), "{}", mobile_book_handler::shm_snapshot(*shm_cache));
				break;
			}
			case 10: {
				auto shm_cache = static_cast<ShmSymbolCache<10>*>(m_shm_symbol_cache_);
				auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<10>>*>(m_shm_manager_);
				shm_cache->m_leg_1_data_shm_cache_.update_counter = 0;
				shm_cache->m_leg_2_data_shm_cache_.update_counter = 0;
				FluxCppCore::StringUtil::setString(shm_cache->m_leg_1_data_shm_cache_.symbol_,
					mr_config_.m_leg_1_symbol_);
				FluxCppCore::StringUtil::setString(shm_cache->m_leg_2_data_shm_cache_.symbol_,
		            mr_config_.m_leg_2_symbol_);
				shm_manager->write_to_shared_memory(*shm_cache);
				LOG_INFO_IMPL(GetCppAppLogger(), "{}", mobile_book_handler::shm_snapshot(*shm_cache));
				break;
			}
			case 15: {
				auto shm_cache = static_cast<ShmSymbolCache<15>*>(m_shm_symbol_cache_);
				auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<15>>*>(m_shm_manager_);
				shm_cache->m_leg_1_data_shm_cache_.update_counter = 0;
				shm_cache->m_leg_2_data_shm_cache_.update_counter = 0;
				FluxCppCore::StringUtil::setString(shm_cache->m_leg_1_data_shm_cache_.symbol_,
					mr_config_.m_leg_1_symbol_);
				FluxCppCore::StringUtil::setString(shm_cache->m_leg_2_data_shm_cache_.symbol_,
		            mr_config_.m_leg_2_symbol_);
				shm_manager->write_to_shared_memory(*shm_cache);
				LOG_INFO_IMPL(GetCppAppLogger(), "{}", mobile_book_handler::shm_snapshot(*shm_cache));
				break;
			}
			case 20: {
				auto shm_cache = static_cast<ShmSymbolCache<20>*>(m_shm_symbol_cache_);
				auto shm_manager = static_cast<SharedMemoryManager<ShmSymbolCache<20>>*>(m_shm_manager_);
				shm_cache->m_leg_1_data_shm_cache_.update_counter = 0;
				shm_cache->m_leg_2_data_shm_cache_.update_counter = 0;
				FluxCppCore::StringUtil::setString(shm_cache->m_leg_1_data_shm_cache_.symbol_,
					mr_config_.m_leg_1_symbol_);
				FluxCppCore::StringUtil::setString(shm_cache->m_leg_2_data_shm_cache_.symbol_,
		            mr_config_.m_leg_2_symbol_);
				shm_manager->write_to_shared_memory(*shm_cache);
				LOG_INFO_IMPL(GetCppAppLogger(), "{}", mobile_book_handler::shm_snapshot(*shm_cache));
				break;
			} default: {
				LOG_ERROR_IMPL(GetCppAppLogger(), "Market Depth level not supported: {};;; supported  levels "
									  "are: 1, 5, 10, 15, 20", mr_config_.m_market_depth_level_);
			}

		}
	}


protected:
    std::atomic<bool> m_shutdown_flag_{false};
    FluxCppCore::Monitor<LastBarterQueueElement> m_last_barter_monitor_{};
    FluxCppCore::Monitor<std::vector<MarketDepthQueueElement>> m_market_depth_monitor_{};
    MarketDepthList m_market_depth_list_{};
    TopOfBook m_top_of_book_{};
    LastBarter m_last_barter_{};
    Config& mr_config_;
    std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_handler_;
    FluxCppCore::MongoDBCodec<MarketDepth, MarketDepthList> m_market_depth_codec_;
    FluxCppCore::MongoDBCodec<LastBarter, LastBarterList> m_last_barter_codec_;
    FluxCppCore::MongoDBCodec<TopOfBook, TopOfBookList> m_top_of_book_codec_;
    FluxCppCore::MongoDBCodec<RawMarketDepthHistory, RawMarketDepthHistoryList> m_raw_market_depth_history_codec_;
    FluxCppCore::MongoDBCodec<RawLastBarterHistory, RawLastBarterHistoryList> m_raw_last_barter_history_codec_;
    void* m_shm_symbol_cache_{};
    void* m_shm_manager_;
public:
    RawLastBarterHistoryList m_raw_last_barter_history_list_{};
    RawMarketDepthHistoryList m_raw_market_depth_history_list_{};
protected:
    std::optional<mobile_book_handler::MobileBookMarketDepthListWebSocketServer<MarketDepthList>> m_market_depth_web_socket_server_{std::nullopt};
    std::optional<mobile_book_handler::MobileBookLastBarterWebSocketServer<LastBarter>> m_last_barter_web_socket_server_{std::nullopt};
    std::optional<mobile_book_handler::MobileBookTopOfBookWebSocketServer<TopOfBook>> m_top_of_book_web_socket_server_{std::nullopt};

	std::optional<FluxCppCore::RootModelWebClient<MarketDepth>> m_md_http_client_;
	std::optional<FluxCppCore::RootModelWebClient<TopOfBook>> m_tob_web_client_;
	std::optional<FluxCppCore::RootModelWebClient<LastBarter>> m_lt_web_client_;

    std::jthread m_market_depth_monitor_thread_{};
    std::jthread m_last_barter_monitor_thread_{};
	std::vector<MarketDepthQueueElement> m_market_depth_queue_element_list_{};

	template<size_t N>
    void update_market_depth_cache(const MarketDepthQueueElement& kr_market_depth_queue_element,
	MDContainer<N>& r_mobile_book_cache_out) const ;

	template<size_t N>
    void update_last_barter_cache(const LastBarterQueueElement& kr_last_barter_queue_element,
	MDContainer<N>& r_mobile_book_cache_out) const ;

     static void populate_market_depth(const MarketDepthQueueElement& kr_market_depth_queue_element,
        MarketDepth& r_market_depth);

    void update_market_depth_db_cache();

    void update_top_of_book_db_cache();

    void initialize_websocket_servers();

    void market_depth_consumer();

    void last_barter_consumer();

    void start_monitor_threads();


	void initialize_webclient() {
		if (mr_config_.m_http_host_.empty() or mr_config_.m_http_port_.empty()) {
			return;
		}

		if (mr_config_.m_last_barter_http_update_publish_policy_ != PublishPolicy::OFF) {
			m_lt_web_client_.emplace(mr_config_.m_http_host_, mr_config_.m_http_port_, mr_config_.m_lt_client_config_);
		}

		if(mr_config_.m_market_depth_http_update_publish_policy_ != PublishPolicy::OFF) {
			m_md_http_client_.emplace(mr_config_.m_http_host_, mr_config_.m_http_port_, mr_config_.m_md_client_config_);
		}

		if (mr_config_.m_top_of_book_http_update_publish_policy_ != PublishPolicy::OFF) {
			m_tob_web_client_.emplace(mr_config_.m_http_host_, mr_config_.m_http_port_, mr_config_.m_tob_client_config_);
		}
	}

	void initialize_shm() {
		switch (mr_config_.m_market_depth_level_) {
    		case 1: {
    			m_shm_symbol_cache_ = new ShmSymbolCache<1>();
    			m_shm_manager_ = new SharedMemoryManager<ShmSymbolCache<1>>(mr_config_.m_shm_cache_name_,
					mr_config_.m_shm_semaphore_name_, mr_config_.m_binary_log_path_);
    			break;
    		} case 5: {
    			m_shm_symbol_cache_ = new ShmSymbolCache<5>();
    			m_shm_manager_ = new SharedMemoryManager<ShmSymbolCache<5>>(mr_config_.m_shm_cache_name_,
					mr_config_.m_shm_semaphore_name_, mr_config_.m_binary_log_path_);
    			break;
    		} case 10: {
    			m_shm_symbol_cache_ = new ShmSymbolCache<10>();
    			m_shm_manager_ = new SharedMemoryManager<ShmSymbolCache<10>>(mr_config_.m_shm_cache_name_,
					mr_config_.m_shm_semaphore_name_, mr_config_.m_binary_log_path_);
    			break;
    		} case 15: {
    			m_shm_symbol_cache_ = new ShmSymbolCache<15>();
    			m_shm_manager_ = new SharedMemoryManager<ShmSymbolCache<15>>(mr_config_.m_shm_cache_name_,
					mr_config_.m_shm_semaphore_name_, mr_config_.m_binary_log_path_);
    			break;
    		} case 20: {
    			m_shm_symbol_cache_ = new ShmSymbolCache<20>();
    			m_shm_manager_ = new SharedMemoryManager<ShmSymbolCache<20>>(mr_config_.m_shm_cache_name_,
					mr_config_.m_shm_semaphore_name_, mr_config_.m_binary_log_path_);
    			break;
    		} default: {
    			throw std::runtime_error("Depth not supported");

    		}
    	}
	}

	void populate_market_depth_queue_element(const MarketDepthQueueElement& kr_market_depth_queue_element, MarketDepth& r_market_depth) const ;

};