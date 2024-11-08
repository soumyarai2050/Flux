#pragma once

#include <optional>
#include <thread>

#include <yaml-cpp/yaml.h>

#include "mobile_book_constants.h"
#include "mongo_db_handler.h"
#include "mongo_db_codec.h"
#include "base_web_client.h"
#include "shared_memory_manager.h"
#include "config_parser.h"
#include "mobile_book_web_socket_server.h"
#include "queue_handler.h"
#include "mobile_book_service_shared_data_structure.h"


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
		mr_config_.m_shm_semaphore_name_) {

		m_last_barter_history_db_codec_.get_all_data_from_collection(m_last_barter_collection_);
		m_market_depth_history_db_codec_.get_all_data_from_collection(m_market_depth_history_collection_);
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

	virtual ~MobileBookPublisher() = default;

	// virtual void go() = 0;

	/*
	 * This function processes market depth data from a queue element. It updates shared memory cache if the publish
	 * policy is set to PRE. It constructs a MarketDepth object with various attributes based on the queue element and
	 * publishes the data to a database, HTTP, and WebSocket based on the specified publish policies.
	 * If the position is 0, it also creates a TopOfBook object and publishes it similarly.
	 * Finally, if any of the publish policies are set to POST, it pushes the original queue element to a monitoring queue.
	 */
	void process_market_depth(const MarketDepthQueueElement& kr_market_depth);

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

	std::jthread md_thread_;
	std::jthread lt_thread_;

	/*
	 * This function updates the shared memory cache with market depth and top of book information
	 * based on the provided market depth queue element.
	 * It checks if the symbol of the market depth element matches either of the configured leg symbols
	 * and updates the corresponding shared memory cache. Finally, it writes the updated cache to shared memory.
	 */
	void update_shm_cache(const MarketDepthQueueElement& kr_market_depth_queue_element);

	/*
	 * This function updates the shared memory cache with last barter and top of book information
	 * based on the provided last barter queue element.
	 * It checks if the symbol of the last barter element matches either of the configured leg symbols
	 * and updates the corresponding shared memory cache. Finally, it writes the updated cache to shared memory.
	 */
	void update_shm_cache(const LastBarterQueueElement& kr_last_barter_queue_element);

	static void update_market_depth_cache(const MarketDepthQueueElement& kr_market_depth_queue_element,
		MobileBookShmCache& r_mobile_book_cache_out);

	static void update_last_barter_cache(const LastBarterQueueElement& kr_last_barter_cache,
		MobileBookShmCache& r_mobile_book_cache_out);

	void create_or_update_market_depth_db(mobile_book::MarketDepth& kr_market_depth);

	void create_or_update_top_of_book_db(mobile_book::TopOfBook& top_of_book);

	void create_or_update_last_barter_db(mobile_book::LastBarter &r_last_barter);

	void create_or_update_market_depth_http(mobile_book::MarketDepth& kr_market_depth);

	void create_or_update_top_of_book_http(mobile_book::TopOfBook &r_top_of_book);

	void create_or_update_last_barter_http(mobile_book::LastBarter &r_last_barter);

	void publish_market_depth_over_ws(mobile_book::MarketDepth& kr_market_depth);

	void publish_last_barter_over_ws(mobile_book::LastBarter &r_last_barter);

	void start_thread() {
		md_thread_ = std::jthread([this]() { md_consumer_thread(); });
		lt_thread_ = std::jthread([this]() { last_barter_consumer_thread(); });
	}

	void md_consumer_thread() {
		MarketDepthQueueElement md;
		mobile_book::MarketDepth market_depth;
		mobile_book::TopOfBook top_of_book;
		while(true) {
			auto status = mon_md.pop(md);
			if (status == FluxCppCore::QueueStatus::DATA_CONSUMED) {

				if (mr_config_.m_market_depth_py_cache_publish_policy_ == PublishPolicy::POST) {
					update_shm_cache(md);
				}

				market_depth.set_id(md.id_);
				market_depth.set_symbol(md.symbol_);
				market_depth.set_exch_time(md.exch_time_);
				market_depth.set_arrival_time(md.arrival_time_);
				if (md.side_ == 'B') {
					market_depth.set_side(mobile_book::TickType::BID);
				} else {
					market_depth.set_side(mobile_book::TickType::ASK);
				}
				if (md.is_px_set_)
					market_depth.set_px(static_cast<float>(md.px_));

				if (md.is_qty_set_) {
					market_depth.set_qty(md.qty_);
				}
				market_depth.set_position(md.position_);
				if (md.is_market_maker_set_) {
					market_depth.set_market_maker(md.market_maker_);
				}

				if (md.is_is_smart_depth_set_) {
					market_depth.set_is_smart_depth(md.is_smart_depth_);
				}
				if (md.is_cumulative_notional_set_) {
					market_depth.set_cumulative_notional(static_cast<float>(md.cumulative_notional_));
				}

				if (md.is_cumulative_qty_set_) {
					market_depth.set_cumulative_qty(md.cumulative_qty_);
				}

				if (md.is_cumulative_avg_px_set_) {
					market_depth.set_cumulative_avg_px(static_cast<float>(md.cumulative_avg_px_));
				}
				if (md.position_ == 0) {
					top_of_book.set_id(1);
					top_of_book.set_symbol(md.symbol_);
					top_of_book.set_last_update_date_time(md.exch_time_);
					if (md.side_ == 'B') {
						top_of_book.mutable_bid_quote()->set_px(static_cast<float>(md.px_));
						top_of_book.mutable_bid_quote()->set_qty(md.qty_);
						top_of_book.mutable_bid_quote()->set_last_update_date_time(md.exch_time_);
					} else {
						top_of_book.mutable_ask_quote()->set_px(static_cast<float>(md.px_));
						top_of_book.mutable_ask_quote()->set_qty(md.qty_);
						top_of_book.mutable_ask_quote()->set_last_update_date_time(md.exch_time_);
					}


					if (mr_config_.m_top_of_book_db_update_publish_policy_ == PublishPolicy::POST) {
						create_or_update_top_of_book_db(top_of_book);
					}

					if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::POST) {
						create_or_update_top_of_book_http(top_of_book);
					}

					if (mr_config_.m_top_of_book_ws_update_publish_policy_ == PublishPolicy::POST) {
						m_top_of_book_web_socket_server_.value().NewClientCallBack(top_of_book, -1);
					}
				}

				if (mr_config_.m_market_depth_db_update_publish_policy_ == PublishPolicy::POST) {
					create_or_update_market_depth_db(market_depth);
				}

				if (mr_config_.m_market_depth_http_update_publish_policy_ == PublishPolicy::POST) {
					create_or_update_market_depth_http(market_depth);
				}

				if (mr_config_.m_market_depth_ws_update_publish_policy_ == PublishPolicy::POST) {
					publish_market_depth_over_ws(market_depth);
				}

				market_depth.Clear();
				top_of_book.Clear();
			}
		}
	}

	void last_barter_consumer_thread() {
		LastBarterQueueElement lt;
		mobile_book::LastBarter last_barter;
		mobile_book::TopOfBook tob;
		while(true)
		{
			auto status = mon_lt.pop(lt);
			if (status == FluxCppCore::QueueStatus::DATA_CONSUMED)
			{
				if (mr_config_.m_last_barter_py_cache_publish_policy_ == PublishPolicy::POST) {
					update_shm_cache(lt);
				}

				last_barter.set_id(lt.id_);
				last_barter.mutable_symbol_n_exch_id()->set_symbol(lt.symbol_n_exch_id_.symbol_);
				last_barter.mutable_symbol_n_exch_id()->set_exch_id(lt.symbol_n_exch_id_.exch_id_);
				last_barter.set_px(static_cast<float>(lt.px_));
				last_barter.set_qty(lt.qty_);
				last_barter.set_exch_time(lt.exch_time_);
				last_barter.set_arrival_time(lt.arrival_time_);
				last_barter.mutable_market_barter_volume()->set_id(lt.market_barter_volume_.id_);
				last_barter.mutable_market_barter_volume()->set_participation_period_last_barter_qty_sum(
					lt.market_barter_volume_.participation_period_last_barter_qty_sum_);
				last_barter.mutable_market_barter_volume()->set_applicable_period_seconds(
					lt.market_barter_volume_.applicable_period_seconds_);

				tob.set_id(1);
				tob.set_symbol(lt.symbol_n_exch_id_.symbol_);
				tob.mutable_last_barter()->set_px(static_cast<float>(lt.px_));
				tob.mutable_last_barter()->set_qty(lt.qty_);
				tob.mutable_last_barter()->set_last_update_date_time(last_barter.exch_time());
				tob.set_last_update_date_time(last_barter.exch_time());
				tob.add_market_barter_volume()->CopyFrom(last_barter.market_barter_volume());

				if (mr_config_.m_top_of_book_db_update_publish_policy_ == PublishPolicy::POST) {
					create_or_update_top_of_book_db(tob);
				}

				if (mr_config_.m_last_barter_db_update_publish_policy_ == PublishPolicy::POST) {
					create_or_update_last_barter_db(last_barter);
				}

				if (mr_config_.m_last_barter_http_update_publish_policy_ == PublishPolicy::POST) {
					create_or_update_last_barter_http(last_barter);
				}

				if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::POST) {
					create_or_update_top_of_book_http(tob);
				}

				if (mr_config_.m_last_barter_ws_update_publish_policy_ == PublishPolicy::POST) {
					publish_last_barter_over_ws(last_barter);
				}
				
				if (mr_config_.m_top_of_book_ws_update_publish_policy_ == PublishPolicy::POST) {
					m_top_of_book_web_socket_server_.value().NewClientCallBack(tob, -1);
				}

				last_barter.Clear();
				tob.Clear();
			}
		}
	}

};
