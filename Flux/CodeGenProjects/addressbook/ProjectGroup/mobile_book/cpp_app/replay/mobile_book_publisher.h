#pragma once

#include <optional>
#include <thread>

#include <yaml-cpp/yaml.h>

#include "mobile_book_constants.h"
#include "mongo_db_handler.h"
#include "mongo_db_codec.h"
#include "base_web_client.h"
#include "shared_memory_manager.h"
#include "../include/config_parser.h"
#include "mobile_book_web_socket_server.h"
#include "queue_handler.h"
#include "mobile_book_service_shared_data_structure.h"
#include "cpp_app_shared_resource.h"
#include "../include/shm_symbol_cache.h"


using namespace mobile_book_handler;
class MobileBookPublisher {
public:

	explicit MobileBookPublisher(Config& config) : mr_config_(config),
	m_sp_mongo_db_(std::make_shared<FluxCppCore::MongoDBHandler>(
		mr_config_.m_mongodb_uri_, mr_config_.m_db_name_)),
	m_top_of_book_db_codec_(m_sp_mongo_db_), m_market_depth_db_codec_(m_sp_mongo_db_),
	m_last_barter_db_codec_(m_sp_mongo_db_), m_market_depth_history_db_codec_(m_sp_mongo_db_),
	m_last_barter_history_db_codec_(m_sp_mongo_db_),
	m_symbols_manager_(mr_config_.m_shm_cache_name_,
		mr_config_.m_shm_semaphore_name_, mr_config_.m_binary_log_path_) {

		m_last_barter_history_db_codec_.get_all_data_from_collection(m_last_barter_collection_);
		m_market_depth_history_db_codec_.get_all_data_from_collection(m_market_depth_history_collection_);
		update_market_depth_db_cache();
		update_top_of_book_db_cache();
		initialize_websocket_servers();
		initialize_webclient();
		start_thread();

		m_shm_symbol_cache_.m_leg_1_data_shm_cache_.update_counter = 0;
		m_shm_symbol_cache_.m_leg_2_data_shm_cache_.update_counter = 0;
		FluxCppCore::StringUtil::setString(m_shm_symbol_cache_.m_leg_1_data_shm_cache_.symbol_,
			mr_config_.m_leg_1_symbol_.c_str(), sizeof(m_shm_symbol_cache_.m_leg_1_data_shm_cache_.symbol_));
		FluxCppCore::StringUtil::setString(m_shm_symbol_cache_.m_leg_2_data_shm_cache_.symbol_,
			mr_config_.m_leg_2_symbol_.c_str(), sizeof(m_shm_symbol_cache_.m_leg_2_data_shm_cache_.symbol_));

		m_symbols_manager_.write_to_shared_memory(m_shm_symbol_cache_);
	}

	virtual ~MobileBookPublisher() {
		shutdown_flag_ = true;
		m_symbols_manager_.~SharedMemoryManager();
		if (md_thread_.joinable() && lt_thread_.joinable()) {
			md_thread_.join();
			lt_thread_.join();
		}
	};

	// virtual void go() = 0;

	/*
	 * This function processes market depth data from a queue element. It updates shared memory cache if the publish
	 * policy is set to PRE. It constructs a MarketDepth object with various attributes based on the queue element and
	 * publishes the data to a database, HTTP, and WebSocket based on the specified publish policies.
	 * If the position is 0, it also creates a TopOfBook object and publishes it similarly.
	 * Finally, if any of the publish policies are set to POST, it pushes the original queue element to a monitoring queue.
	 */
	void process_market_depth(MarketDepthQueueElement& kr_market_depth);

	/*
	 * This function processes the last barter data received from a queue element.
	 * It updates shared memory cache based on the publish policy, constructs a LastBarter data object,
	 * and publishes it to various outputs (database, HTTP, WebSocket) based on the respective publish policies.
	 * Additionally, it constructs a TopOfBook object and publishes it accordingly.
	 * If any of the publish policies are set to POST, it pushes the barter data back onto the queue for further processing.
	 */
	void process_last_barter(const LastBarterQueueElement& last_barter);


protected:
	void initialize_websocket_servers() {
		if (mr_config_.m_top_of_book_ws_update_publish_policy_ != PublishPolicy::OFF) {
			m_top_of_book_web_socket_server_.emplace(m_top_of_book_, host, mr_config_.m_top_of_book_ws_port_,
												 std::chrono::seconds(mobile_book_handler::connection_timeout));
		}
		if (mr_config_.m_last_barter_ws_update_publish_policy_ != PublishPolicy::OFF) {
			m_last_barter_web_socket_server_.emplace(m_last_barter_, host, mr_config_.m_last_barter_ws_port_,
												std::chrono::seconds(mobile_book_handler::connection_timeout));
		}
		if (mr_config_.m_market_depth_ws_update_publish_policy_ != PublishPolicy::OFF) {
			m_market_depth_web_socket_server_.emplace(m_market_depth_, host, mr_config_.m_market_depth_ws_port_,
												  std::chrono::seconds(mobile_book_handler::connection_timeout));
		}
	}

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

		if (mr_config_.m_top_of_book_ws_update_publish_policy_ != PublishPolicy::OFF) {
			m_tob_web_client_.emplace(mr_config_.m_http_host_, mr_config_.m_http_port_, mr_config_.m_tob_client_config_);
		}
	}


	std::atomic<bool> shutdown_flag_{false};
	FluxCppCore::Monitor<LastBarterQueueElement> mon_lt{};
	FluxCppCore::Monitor<MarketDepthQueueElement> mon_md{};

	ShmSymbolCache m_shm_symbol_cache_{};

	mobile_book::TopOfBook m_top_of_book_{};
	mobile_book::LastBarter m_last_barter_{};
	mobile_book::MarketDepth m_market_depth_{};

	Config& mr_config_;
	std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
	FluxCppCore::MongoDBCodec<mobile_book::TopOfBook, mobile_book::TopOfBookList> m_top_of_book_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::MarketDepth, mobile_book::MarketDepthList> m_market_depth_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::LastBarter, mobile_book::LastBarterList> m_last_barter_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::RawMarketDepthHistory, mobile_book::RawMarketDepthHistoryList>
	m_market_depth_history_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::RawLastBarterHistory, mobile_book::RawLastBarterHistoryList>
	m_last_barter_history_db_codec_;

	SharedMemoryManager<ShmSymbolCache> m_symbols_manager_;

public:
	mobile_book::RawLastBarterHistoryList m_last_barter_collection_{};
	mobile_book::RawMarketDepthHistoryList m_market_depth_history_collection_{};

protected:
	std::optional<mobile_book_handler::MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth>> m_market_depth_web_socket_server_{std::nullopt};
	std::optional<mobile_book_handler::MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook>>  m_top_of_book_web_socket_server_{std::nullopt};
	std::optional<mobile_book_handler::MobileBookLastBarterWebSocketServer<mobile_book::LastBarter>> m_last_barter_web_socket_server_{std::nullopt};


	std::optional<FluxCppCore::RootModelWebClient<mobile_book::MarketDepth>> m_md_http_client_;
	std::optional<FluxCppCore::RootModelWebClient<mobile_book::TopOfBook>> m_tob_web_client_;
	std::optional<FluxCppCore::RootModelWebClient<mobile_book::LastBarter>> m_lt_web_client_;

	std::thread md_thread_;
	std::thread lt_thread_;

	/*
	 * This function updates the shared memory cache with market depth and top of book information
	 * based on the provided market depth queue element.
	 * It checks if the symbol of the market depth element matches either of the configured leg symbols
	 * and updates the corresponding shared memory cache. Finally, it writes the updated cache to shared memory.
	 */
	void update_shm_cache(MarketDepthQueueElement& kr_market_depth_queue_element);

	/*
	 * This function updates the shared memory cache with last barter and top of book information
	 * based on the provided last barter queue element.
	 * It checks if the symbol of the last barter element matches either of the configured leg symbols
	 * and updates the corresponding shared memory cache. Finally, it writes the updated cache to shared memory.
	 */
	void update_shm_cache(const LastBarterQueueElement& kr_last_barter_queue_element);

	static void update_market_depth_cache(const MarketDepthQueueElement& kr_market_depth_queue_element,
		MDContainer& r_mobile_book_cache_out);

	static void update_last_barter_cache(const LastBarterQueueElement& kr_last_barter_cache,
		MDContainer& r_mobile_book_cache_out);

	void create_or_update_market_depth_db(mobile_book::MarketDepth& kr_market_depth);

	void create_or_update_top_of_book_db(mobile_book::TopOfBook& top_of_book);

	void create_or_update_last_barter_db(mobile_book::LastBarter &r_last_barter);

	void create_or_update_market_depth_http(mobile_book::MarketDepth& kr_market_depth);

	void create_or_update_top_of_book_http(mobile_book::TopOfBook &r_top_of_book);

	void create_or_update_last_barter_http(mobile_book::LastBarter &r_last_barter);

	void publish_market_depth_over_ws(mobile_book::MarketDepth& kr_market_depth);

	void publish_last_barter_over_ws(mobile_book::LastBarter &r_last_barter);

	void start_thread() {
		md_thread_ = std::thread([this]() { md_consumer_thread(); });
		lt_thread_ = std::thread([this]() { last_barter_consumer_thread(); });
	}

	void md_consumer_thread();

	void last_barter_consumer_thread();

	void update_market_depth_db_cache() {
		mobile_book::MarketDepthList market_depth_list;
		m_market_depth_db_codec_.get_all_data_from_collection(market_depth_list);
		std::vector<std::string> market_depth_key_list;
		MobileBookKeyHandler::get_key_list(market_depth_list, market_depth_key_list);
		for (int i{0}; i < market_depth_list.market_depth_size(); ++i) {
            m_market_depth_db_codec_.m_root_model_key_to_db_id[
            	market_depth_key_list[i]] = market_depth_list.market_depth(i).id();
        }
	}

	void update_top_of_book_db_cache() {
		mobile_book::TopOfBookList tob_list;
        m_top_of_book_db_codec_.get_all_data_from_collection(tob_list);
        std::vector<std::string> tob_key_list;
		MobileBookKeyHandler::get_key_list(tob_list, tob_key_list);
        for (int i{0}; i < tob_list.top_of_book_size(); ++i) {
            m_top_of_book_db_codec_.m_root_model_key_to_db_id[
                tob_key_list[i]] = tob_list.top_of_book(i).id();
        }

	}

};
