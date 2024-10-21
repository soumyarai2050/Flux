#pragma once

#include "base_web_client.h"
#include "mobile_book_web_socket_server.h"
#include "mongo_db_codec.h"
#include "queue_handler.h"
#include "mobile_book_service_shared_data_structure.h"
#include "mobile_book_service.pb.h"
#include "mongo_db_handler.h"
#include "mobile_book_constants.h"
#include "cpp_app_shared_resource.h"


class MobileBookInterface {
public:
	virtual ~MobileBookInterface() = default;

	virtual void go() = 0;

protected:

	explicit MobileBookInterface(
		const std::string &kr_yaml_config_file) :
	k_mr_config_file_(kr_yaml_config_file), m_config_file_(YAML::LoadFile(k_mr_config_file_)),
	km_project_name_((get_project_name())), m_top_of_book_ws_port_(get_top_of_book_ws_port()),
	m_last_barter_ws_port_(get_last_barter_ws_port()), m_market_depth_ws_port_(get_market_depth_ws_port()),
	m_http_client_host_(get_http_ip()), m_http_client_port_(get_http_port()),
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

	}

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

	mobile_book::RawLastBarterHistoryList m_last_barter_collection_{};
	mobile_book::RawMarketDepthHistoryList m_market_depth_history_collection_{};

	std::optional<mobile_book_handler::MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth>> m_market_depth_web_socket_server_{std::nullopt};
	std::optional<mobile_book_handler::MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook>>  m_top_of_book_web_socket_server_{std::nullopt};
	std::optional<mobile_book_handler::MobileBookLastBarterWebSocketServer<mobile_book::LastBarter>> m_last_barter_web_socket_server_{std::nullopt};


	std::optional<FluxCppCore::RootModelWebClient<mobile_book::MarketDepth>> m_md_http_client_;
	std::optional<FluxCppCore::RootModelWebClient<mobile_book::TopOfBook>> m_tob_web_client_;
	std::optional<FluxCppCore::RootModelWebClient<mobile_book::LastBarter>> m_lt_web_client_;


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

};



class MobileBookConsumer : public MobileBookInterface {
public:
	explicit MobileBookConsumer(const std::string& kr_config_file) : MobileBookInterface(kr_config_file) {
		start_thread();
		update_tob_db_cache();
		update_md_db_cache();
	}

	void go() override {
		int market_depth_index = 0;
		int last_barter_index = 0;

		while (market_depth_index < m_market_depth_history_collection_.raw_market_depth_history_size() or
			last_barter_index < m_last_barter_collection_.raw_last_barter_history_size()) {
			if (market_depth_index < m_market_depth_history_collection_.raw_market_depth_history_size() and
				last_barter_index >= m_last_barter_collection_.raw_last_barter_history_size()) {

				char side;
				if (m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).side() ==
					mobile_book::TickType::BID) {
					side = 'B';
					} else {
						side = 'A';
					}

				MarketDepth mkt_depth;
				mkt_depth.id_ = m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).id();
				mkt_depth.symbol_ = m_market_depth_history_collection_.raw_market_depth_history(
					market_depth_index).symbol_n_exch_id().symbol();
				mkt_depth.exch_time_ = m_market_depth_history_collection_.raw_market_depth_history(
					market_depth_index).exch_time();
				mkt_depth.arrival_time_ = m_market_depth_history_collection_.raw_market_depth_history(
					market_depth_index).arrival_time();
				mkt_depth.side_ = side;
				if (m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).has_px()) {
					mkt_depth.px_ = m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).px();
					mkt_depth.is_px_set_ = true;
				} else {
					mkt_depth.px_ = 0;
					mkt_depth.is_px_set_ = false;
				}

				if (m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).has_qty()) {
					mkt_depth.qty_ = m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).qty();
					mkt_depth.is_qty_set_ = true;
				} else {
					mkt_depth.qty_ = 0;
					mkt_depth.is_qty_set_ = false;
				}
				mkt_depth.position_ = m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).position();
				mkt_depth.market_maker_ = "";
				mkt_depth.is_market_maker_set_ = false;
				mkt_depth.is_smart_depth_ = false;
				mkt_depth.is_is_smart_depth_set_ = false;
				mkt_depth.cumulative_notional_ = 0.0;
				mkt_depth.is_cumulative_notional_set_ = false;
				mkt_depth.cumulative_qty_ = 0;
				mkt_depth.is_cumulative_qty_set_ = false;
				mkt_depth.cumulative_avg_px_ = 0;
				mkt_depth.is_cumulative_avg_px_set_ = false;

				process_market_depth(mkt_depth);
				++market_depth_index;

			} else {

				// Replay last barter

				LastBarter last_barter;
				last_barter.id_ = m_last_barter_collection_.raw_last_barter_history(last_barter_index).id();
				last_barter.symbol_n_exch_id_.symbol_ = m_last_barter_collection_.raw_last_barter_history(
					last_barter_index).symbol_n_exch_id().symbol();
				last_barter.symbol_n_exch_id_.exch_id_ = m_last_barter_collection_.raw_last_barter_history(
					last_barter_index).symbol_n_exch_id().exch_id();
				last_barter.exch_time_ = m_last_barter_collection_.raw_last_barter_history(last_barter_index).exch_time();
				last_barter.arrival_time_ = m_last_barter_collection_.raw_last_barter_history(last_barter_index).arrival_time();
				last_barter.px_ = m_last_barter_collection_.raw_last_barter_history(last_barter_index).px();
				last_barter.qty_ = m_last_barter_collection_.raw_last_barter_history(last_barter_index).qty();
				if (m_last_barter_collection_.raw_last_barter_history(last_barter_index).has_premium()) {
					last_barter.premium_ = m_last_barter_collection_.raw_last_barter_history(last_barter_index).premium();
					last_barter.is_premium_set_ = true;
				} else {
					last_barter.premium_ = 0;
					last_barter.is_premium_set_ = false;
				}

				if (m_last_barter_collection_.raw_last_barter_history(last_barter_index).has_market_barter_volume()) {
					last_barter.market_barter_volume_.id_ = m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).market_barter_volume().id();
					if (m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).market_barter_volume().has_participation_period_last_barter_qty_sum()) {
						last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_ =
							m_last_barter_collection_.raw_last_barter_history(
								last_barter_index).market_barter_volume().participation_period_last_barter_qty_sum();
						last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = true;
					} else {
						last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_ = 0;
						last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = false;
					}

					if (m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).market_barter_volume().has_applicable_period_seconds()) {
						last_barter.market_barter_volume_.applicable_period_seconds_ =
							m_last_barter_collection_.raw_last_barter_history(
								last_barter_index).market_barter_volume().applicable_period_seconds();
						last_barter.market_barter_volume_.is_applicable_period_seconds_set_ = true;
					} else {
						last_barter.market_barter_volume_.applicable_period_seconds_ = 0;
						last_barter.market_barter_volume_.is_applicable_period_seconds_set_ = false;
					}
					last_barter.is_market_barter_volume_set_ = true;
				} else {
					last_barter.market_barter_volume_.id_ = "";
					last_barter.market_barter_volume_.applicable_period_seconds_ = 0;
					last_barter.market_barter_volume_.is_applicable_period_seconds_set_ = false;
					last_barter.market_barter_volume_.participation_period_last_barter_qty_sum_ = 0;
					last_barter.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_ = false;
					last_barter.is_market_barter_volume_set_ = false;
				}
				process_last_barter(last_barter);

				++last_barter_index;
			}
		}
		LOG_INFO_IMPL(GetCppAppLogger(), "exit: {}", __func__);
	}

	void process_market_depth(const MarketDepth &md) {
		LOG_INFO_IMPL(GetCppAppLogger(), "inside: {}: {}", __func__, md.symbol_);
		mon_md.push(md);
		PyMarketDepth md_market_depth{md.symbol_.c_str(), md.exch_time_.c_str(),
			md.arrival_time_.c_str(), md.side_, md.px_, md.is_px_set_, md.qty_, md.is_qty_set_,
			md.position_, md.market_maker_.c_str(), md.is_market_maker_set_, md.is_smart_depth_,
			md.is_is_smart_depth_set_, md.cumulative_notional_, md.is_cumulative_notional_set_, md.cumulative_qty_,
			md.is_cumulative_qty_set_, md.cumulative_avg_px_, md.is_cumulative_avg_px_set_};
		LOG_INFO_IMPL(GetCppAppLogger(), "process_market_depth cache: {}", md.symbol_);
		mkt_depth_fp(&md_market_depth);
		LOG_INFO_IMPL(GetCppAppLogger(), "exit: {}: {}", __func__, md.symbol_);
	}

	void process_last_barter(const LastBarter &e) {
		mon_lt.push(e);
		PyLastBarter last_barter{{e.symbol_n_exch_id_.symbol_.c_str(),
			e.symbol_n_exch_id_.exch_id_.c_str()}, e.exch_time_.c_str(), e.arrival_time_.c_str(),
			e.px_, e.qty_, e.premium_, e.is_premium_set_,
			{e.market_barter_volume_.id_.c_str(),
				e.market_barter_volume_.participation_period_last_barter_qty_sum_,
				e.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_,
				e.market_barter_volume_.applicable_period_seconds_,
				e.market_barter_volume_.is_applicable_period_seconds_set_},
			e.is_market_barter_volume_set_};
		last_barter_fp(&last_barter);
	}

protected:
	std::jthread md_thread_;
	std::jthread lt_thread_;
	FluxCppCore::Monitor<LastBarter> mon_lt{};
	FluxCppCore::Monitor<MarketDepth> mon_md{};

	void update_tob_db_cache() {
		mobile_book::TopOfBookList top_of_book_list_documents;
		std::vector<std::string> list_document_keys_vector;
		m_top_of_book_db_codec_.get_all_data_from_collection(top_of_book_list_documents);
		MobileBookKeyHandler::get_key_list(top_of_book_list_documents, list_document_keys_vector);
		for (int i = 0; i < top_of_book_list_documents.top_of_book_size(); ++i) {
			m_top_of_book_db_codec_.m_root_model_key_to_db_id[list_document_keys_vector.at(i)] = top_of_book_list_documents.top_of_book(i).id();
		}
	}

    void update_md_db_cache() {
		mobile_book::MarketDepthList md_list_documents;
		std::vector<std::string> list_document_keys_vector;
		m_market_depth_db_codec_.get_all_data_from_collection(md_list_documents);
		MobileBookKeyHandler::get_key_list(md_list_documents, list_document_keys_vector);
		for (int i = 0; i < md_list_documents.market_depth_size(); ++i) {
			m_market_depth_db_codec_.m_root_model_key_to_db_id[list_document_keys_vector.at(i)] = md_list_documents.market_depth(i).id();
		}
	}

	void md_consumer_thread() {
		MarketDepth md;
		mobile_book::MarketDepth market_depth;
		mobile_book::TopOfBook top_of_book;
		while(true) {
			auto status = mon_md.pop(md);
			if (status == FluxCppCore::QueueStatus::DATA_CONSUMED) {
				std::cout << "md_consumer_thread: mobile_book consumed" << std::endl;
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

					auto tob_db_id = m_top_of_book_db_codec_.insert_or_update(top_of_book);
					top_of_book.set_id(tob_db_id);
					if (m_top_of_book_web_socket_server_) {
						m_top_of_book_web_socket_server_.value().NewClientCallBack(top_of_book, -1);
					}
					if (m_tob_web_client_) {
						std::string top_of_book_key;
						MobileBookKeyHandler::get_key_out(top_of_book, top_of_book_key);
						auto found = m_top_of_book_db_codec_.m_root_model_key_to_db_id.find(top_of_book_key);
						if (found == m_top_of_book_db_codec_.m_root_model_key_to_db_id.end()) {
							assert(m_tob_web_client_.value().create_client(top_of_book));
						} else {
							assert(m_tob_web_client_.value().patch_client(top_of_book));
						}
					}
				}
				[[maybe_unused]] auto db_id = m_market_depth_db_codec_.insert_or_update(market_depth);
				market_depth.set_id(db_id);
				if (m_market_depth_web_socket_server_) {
					m_market_depth_web_socket_server_.value().NewClientCallBack(market_depth, -1);
				}
				if (m_md_http_client_){
					std::string md_key;
					MobileBookKeyHandler::get_key_out(market_depth, md_key);
					auto found = m_market_depth_db_codec_.m_root_model_key_to_db_id.find(md_key);
					if (found == m_market_depth_db_codec_.m_root_model_key_to_db_id.end()) {
						assert(m_md_http_client_.value().create_client(market_depth));
					} else {
						assert(m_md_http_client_.value().patch_client(market_depth));
					}
				}
				market_depth.Clear();
				top_of_book.Clear();
			}
		}
	}

	void last_barter_consumer_thread() {
		LastBarter lt;
		mobile_book::LastBarter last_barter;
		mobile_book::TopOfBook tob;
		while(true)
		{
			auto status = mon_lt.pop(lt);
			if (status == FluxCppCore::QueueStatus::DATA_CONSUMED)
			{
				std::cout << "Market data consumed" << std::endl;
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
				auto tob_db_id = m_top_of_book_db_codec_.insert_or_update(tob);
				auto lt_db_id  = m_last_barter_db_codec_.insert(last_barter);
				tob.set_id(tob_db_id);
				last_barter.set_id(lt_db_id);
				if (m_last_barter_web_socket_server_) {
					m_last_barter_web_socket_server_.value().NewClientCallBack(last_barter, -1);
				}
				if (m_top_of_book_web_socket_server_) {
					m_top_of_book_web_socket_server_.value().NewClientCallBack(tob, -1);
				}

				if (m_lt_web_client_) {
					assert(m_lt_web_client_.value().create_client(last_barter));
				}

				if (m_tob_web_client_) {
					std::string top_of_book_key;
					MobileBookKeyHandler::get_key_out(tob, top_of_book_key);
					auto found = m_top_of_book_db_codec_.m_root_model_key_to_db_id.find(top_of_book_key);
					if (found == m_top_of_book_db_codec_.m_root_model_key_to_db_id.end()) {
						assert(m_tob_web_client_.value().create_client(tob));
					} else {
						assert(m_tob_web_client_.value().patch_client(tob));
					}
				}
				last_barter.Clear();
				tob.Clear();
			}
		}
	}

	void start_thread() {
		md_thread_ = std::jthread([this]() { md_consumer_thread(); });
		lt_thread_ = std::jthread([this]() { last_barter_consumer_thread(); });
	}

};
