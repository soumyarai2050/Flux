#pragma once

#include <optional>
#include <thread>

#include <yaml-cpp/yaml.h>

#include "mobile_book_constants.h"
#include "mongo_db_handler.h"
#include "mongo_db_codec.h"
#include "base_web_client.h"
#include "mobile_book_web_socket_server.h"
#include "queue_handler.h"
#include "cpp_app_shared_resource.h"


using namespace mobile_book_handler;
class MobileBookPublisher {
public:
	virtual ~MobileBookPublisher() = default;

	// virtual void go() = 0;

	void process_market_depth(const MarketDepthQueueElement& market_depth) {
		mon_md.push(market_depth);
	}

	void process_last_barter(const LastBarterQueueElement& last_barter) {
		mon_lt.push(last_barter);
	}

	explicit MobileBookPublisher(
		const std::string &kr_yaml_config_file) :
	k_mr_config_file_(kr_yaml_config_file), m_config_file_(YAML::LoadFile(k_mr_config_file_)),
	km_project_name_((get_project_name())), m_top_of_book_ws_port_(get_top_of_book_ws_port()),
	m_last_barter_ws_port_(get_last_barter_ws_port()), m_market_depth_ws_port_(get_market_depth_ws_port()),
	m_http_client_host_(get_http_ip()), m_http_client_port_(get_http_port()),
	m_avoid_market_depth_db_update_(avoid_market_depth_db_update()),
	m_avoid_top_of_book_db_update_(avoid_top_of_book_db_update()),
	m_avoid_last_barter_db_update_(avoid_last_barter_db_update()),
	m_md_client_config_(
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + create_market_depth_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + get_market_depth_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + get_market_depth_max_id_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + put_market_depth_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + patch_market_depth_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + delete_market_depth_client_url
		),
	m_tob_client_config_(
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + create_top_of_book_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + get_top_of_book_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + get_top_of_book_max_id_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + put_top_of_book_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + patch_top_of_book_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + delete_top_of_book_client_url
		),
	m_lt_client_config_(
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + create_last_barter_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + get_last_barter_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + get_last_barter_max_id_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + put_last_barter_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + patch_last_barter_client_url,
		PATH_SEPARATOR + km_project_name_ + PATH_SEPARATOR + delete_last_barter_client_url
		),
	m_sp_mongo_db_(std::make_shared<FluxCppCore::MongoDBHandler>(get_db_uri(), get_db_name())),
	m_top_of_book_db_codec_(m_sp_mongo_db_), m_market_depth_db_codec_(m_sp_mongo_db_),
	m_last_barter_db_codec_(m_sp_mongo_db_), m_market_depth_history_db_codec_(m_sp_mongo_db_),
	m_last_barter_history_db_codec_(m_sp_mongo_db_) {

		m_last_barter_history_db_codec_.get_all_data_from_collection(m_last_barter_collection_);
		m_market_depth_history_db_codec_.get_all_data_from_collection(m_market_depth_history_collection_);
		initialize_websocket_servers();
		initialize_webclient();
		start_thread();

	}

protected:
	void initialize_websocket_servers() {
		if (m_top_of_book_ws_port_) {
			m_top_of_book_web_socket_server_.emplace(m_top_of_book_, host, get_top_of_book_ws_port(),
												 std::chrono::seconds(mobile_book_handler::connection_timeout));
		}
		if (m_last_barter_ws_port_) {
			m_last_barter_web_socket_server_.emplace(m_last_barter_, host, get_last_barter_ws_port(),
												std::chrono::seconds(mobile_book_handler::connection_timeout));
		}
		if (m_market_depth_ws_port_) {
			m_market_depth_web_socket_server_.emplace(m_market_depth_, host, get_market_depth_ws_port(),
												  std::chrono::seconds(mobile_book_handler::connection_timeout));
		}
	}

	void initialize_webclient() {
		if (m_http_client_host_.empty() or m_http_client_port_.empty()) {
			return;
		}

		if (!avoid_last_barter_http_update()) {
			m_lt_web_client_.emplace(m_http_client_host_, m_http_client_port_, m_lt_client_config_);
		}

		if(!avoid_market_depth_http_update()) {
			m_md_http_client_.emplace(m_http_client_host_, m_http_client_port_, m_md_client_config_);
		}

		if (!avoid_top_of_book_http_update()) {
			m_tob_web_client_.emplace(m_http_client_host_, m_http_client_port_, m_tob_client_config_);
		}
	}


	FluxCppCore::Monitor<LastBarterQueueElement> mon_lt{};
	FluxCppCore::Monitor<MarketDepthQueueElement> mon_md{};

	mobile_book::TopOfBook m_top_of_book_{};
	mobile_book::LastBarter m_last_barter_{};
	mobile_book::MarketDepth m_market_depth_{};

	const std::string &k_mr_config_file_;
	YAML::Node m_config_file_;
	std::string km_project_name_;
	int32_t m_top_of_book_ws_port_;
	int32_t m_last_barter_ws_port_;
	int32_t m_market_depth_ws_port_;
	std::string m_http_client_host_;
	std::string m_http_client_port_;
	bool m_avoid_market_depth_db_update_;
	bool m_avoid_top_of_book_db_update_;
	bool m_avoid_last_barter_db_update_;
	FluxCppCore::ClientConfig m_md_client_config_;
	FluxCppCore::ClientConfig m_tob_client_config_;
	FluxCppCore::ClientConfig m_lt_client_config_;

	std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
	FluxCppCore::MongoDBCodec<mobile_book::TopOfBook, mobile_book::TopOfBookList> m_top_of_book_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::MarketDepth, mobile_book::MarketDepthList> m_market_depth_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::LastBarter, mobile_book::LastBarterList> m_last_barter_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::RawMarketDepthHistory, mobile_book::RawMarketDepthHistoryList>
	m_market_depth_history_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::RawLastBarterHistory, mobile_book::RawLastBarterHistoryList>
	m_last_barter_history_db_codec_;

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


	std::string get_db_uri() const {
		return m_config_file_["mongo_server"].as<std::string>();
	}

	std::string get_db_name() const {
		return m_config_file_["db_name"].as<std::string>();
	}

	int32_t get_top_of_book_ws_port() const {
		return m_config_file_["top_of_book_ws_port"].IsDefined() ? m_config_file_["top_of_book_ws_port"].as<int32_t>() : 0;
	}

	int32_t get_last_barter_ws_port() const {
		return m_config_file_["last_barter_ws_port"].IsDefined() ? m_config_file_["last_barter_ws_port"].as<int32_t>() : 0;
	}

	int32_t get_market_depth_ws_port() const {
		return m_config_file_["market_depth_ws_port"].IsDefined() ? m_config_file_["market_depth_ws_port"].as<int32_t>() : 0;
	}

	auto get_ws_timeout() const {
		auto timeout =  m_config_file_["websocket_timeout"].IsDefined() ? m_config_file_["websocket_timeout"].as<int32_t>() : 0;
		return std::chrono::seconds(timeout);
	}

	int32_t get_ws_retry_count() const {
		int32_t retry_count = 0;
		try {
			retry_count = m_config_file_["websocket_retry_count"].IsDefined() ? m_config_file_["websocket_retry_count"].as<int32_t>() : 0;
		} catch (std::exception &e) {
			std::cerr << "[" << __FILE__ << ": " << __LINE__ << "] " << e.what() << std::endl;
		}
		return retry_count;
	}

	std::string get_project_name() const {
		return m_config_file_["project_name"].IsDefined() ? m_config_file_["project_name"].as<std::string>() : std::string();
	}

	std::string get_http_ip() const {
		return m_config_file_["http_ip"].IsDefined() ? m_config_file_["http_ip"].as<std::string>() : std::string();
	}

	std::string get_http_port() const {
		return m_config_file_["http_port"].IsDefined() ? m_config_file_["http_port"].as<std::string>() : std::string();
	}

	bool avoid_last_barter_http_update() const {
		return m_config_file_["avoid_last_barter_http_update"].IsDefined() ?
			m_config_file_["avoid_last_barter_http_update"].as<bool>() : true;
	}

	bool avoid_market_depth_http_update () const {
		return m_config_file_["avoid_market_depth_http_update"].IsDefined() ?
			m_config_file_["avoid_market_depth_http_update"].as<bool>() : true;
	}

	bool avoid_top_of_book_http_update () const {
		return m_config_file_["avoid_top_of_book_http_update"].IsDefined() ?
			m_config_file_["avoid_top_of_book_http_update"].as<bool>() : true;
	}

	bool avoid_last_barter_db_update () const {
		return m_config_file_["avoid_last_barter_db_update"].IsDefined() ?
			m_config_file_["avoid_last_barter_db_update"].as<bool>() : true;
	}

	bool avoid_market_depth_db_update () const {
		return m_config_file_["avoid_market_depth_db_update"].IsDefined() ?
			m_config_file_["avoid_market_depth_db_update"].as<bool>() : true;
	}

	bool avoid_top_of_book_db_update () const {
		return m_config_file_["avoid_top_of_book_db_update"].IsDefined() ?
			m_config_file_["avoid_top_of_book_db_update"].as<bool>() : true;
	}

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

					int32_t top_of_book_max_id{0};

					if (!m_avoid_top_of_book_db_update_) {
						auto tob_db_id = m_top_of_book_db_codec_.insert_or_update(top_of_book);
						if (tob_db_id == -1) {
							tob_db_id = m_top_of_book_db_codec_.get_max_id_from_collection();
							++tob_db_id;
						}
						top_of_book.set_id(tob_db_id);
					} else {
						top_of_book_max_id = m_top_of_book_db_codec_.get_max_id_from_collection();
						++top_of_book_max_id;
						top_of_book.set_id(top_of_book_max_id);
					}

					if (m_top_of_book_web_socket_server_) {
						m_top_of_book_web_socket_server_.value().NewClientCallBack(top_of_book, -1);
					}

					if (m_tob_web_client_) {
						std::string top_of_book_key;
						MobileBookKeyHandler::get_key_out(top_of_book, top_of_book_key);
						auto found = m_top_of_book_db_codec_.m_root_model_key_to_db_id.find(top_of_book_key);
						if (found == m_top_of_book_db_codec_.m_root_model_key_to_db_id.end()) {
							assert(m_tob_web_client_.value().create_client(top_of_book));
							if (m_avoid_top_of_book_db_update_) {
								m_top_of_book_db_codec_.m_root_model_key_to_db_id[top_of_book_key] = top_of_book.id();
							}
						} else {
							top_of_book.set_id(found->second);
							assert(m_tob_web_client_.value().patch_client(top_of_book));
						}
					}
				}

				int32_t market_depth_max_id{0};
				if (!m_avoid_market_depth_db_update_) {
					auto db_id = m_market_depth_db_codec_.insert_or_update(market_depth);
					if (db_id == -1) {
						db_id = m_market_depth_db_codec_.get_max_id_from_collection();
						++db_id;
					}
					market_depth.set_id(db_id);
				} else {
					market_depth_max_id = m_market_depth_db_codec_.get_max_id_from_collection();
					++market_depth_max_id;
					market_depth.set_id(market_depth_max_id);
				}

				if (m_market_depth_web_socket_server_) {
					m_market_depth_web_socket_server_.value().NewClientCallBack(market_depth, -1);
				}

				if (m_md_http_client_) {
					std::string md_key;
					MobileBookKeyHandler::get_key_out(market_depth, md_key);
					auto found = m_market_depth_db_codec_.m_root_model_key_to_db_id.find(md_key);
					if (found == m_market_depth_db_codec_.m_root_model_key_to_db_id.end()) {
						assert(m_md_http_client_.value().create_client(market_depth));
						if (m_avoid_market_depth_db_update_) {
							m_market_depth_db_codec_.m_root_model_key_to_db_id[md_key] = market_depth.id();
						}
					} else {
						market_depth.set_id(found->second);
						assert(m_md_http_client_.value().patch_client(market_depth));
					}
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

				int32_t top_of_book_max_id{0};
				int32_t last_barter_max_id{0};

				if (!m_avoid_top_of_book_db_update_) {
					auto tob_db_id = m_top_of_book_db_codec_.insert_or_update(tob);
					if (tob_db_id == -1) {
						tob_db_id = m_top_of_book_db_codec_.get_max_id_from_collection();
						++tob_db_id;
					}
					tob.set_id(tob_db_id);
				} else {
					top_of_book_max_id = m_top_of_book_db_codec_.get_max_id_from_collection();
					++top_of_book_max_id;
					tob.set_id(top_of_book_max_id);
				}

				if (!m_avoid_last_barter_db_update_) {
					auto lt_db_id  = m_last_barter_db_codec_.insert(last_barter);
					if (lt_db_id == -1) {
						lt_db_id  = m_last_barter_db_codec_.get_max_id_from_collection();
						++lt_db_id;
					}
					last_barter.set_id(lt_db_id);
				} else {
					last_barter_max_id = m_last_barter_db_codec_.get_max_id_from_collection();
					++last_barter_max_id;
					last_barter.set_id(last_barter_max_id);
				}

				if (m_last_barter_web_socket_server_) {
					m_last_barter_web_socket_server_.value().NewClientCallBack(last_barter, -1);
				}
				
				if (m_top_of_book_web_socket_server_) {
					m_top_of_book_web_socket_server_.value().NewClientCallBack(tob, -1);
				}

				if (m_lt_web_client_) {
					if (!m_lt_web_client_.value().create_client(last_barter)) {
						LOG_WARNING_IMPL(GetCppAppLogger(), "Error while creating last_barter to web client obj: {}",
							last_barter.DebugString());
					}
				}

				if (m_tob_web_client_) {
					std::string top_of_book_key;
					MobileBookKeyHandler::get_key_out(tob, top_of_book_key);
					auto found = m_top_of_book_db_codec_.m_root_model_key_to_db_id.find(top_of_book_key);
					if (found == m_top_of_book_db_codec_.m_root_model_key_to_db_id.end()) {
						assert(m_tob_web_client_.value().create_client(tob));
						if (m_avoid_top_of_book_db_update_) {
							m_top_of_book_db_codec_.m_root_model_key_to_db_id[top_of_book_key] = tob.id();
						}
					} else {
						tob.set_id(found->second);
						assert(m_tob_web_client_.value().patch_client(tob));
					}
				}
				last_barter.Clear();
				tob.Clear();
			}
		}
	}

};
