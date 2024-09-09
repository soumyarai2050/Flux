#pragma once

#include "string_util.h"
#include "mobile_book_web_socket_server.h"
#include "mongo_db_codec.h"
#include "queue_handler.h"



class MobileBookInterface {
public:
	virtual ~MobileBookInterface() = default;

	virtual void go() = 0;

protected:
	MobileBookInterface(std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db,
		mobile_book_handler::MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook> &r_top_of_book_websocket_server,
		mobile_book_handler::MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> &r_last_barter_websocket_server,
		mobile_book_handler::MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> &r_market_depth_websocket_server) :
	m_sp_mongo_db_(std::move(sp_mongo_db)),  m_top_of_book_db_codec_(m_sp_mongo_db_), m_market_depth_db_codec_(m_sp_mongo_db_),
	m_last_barter_db_codec_(m_sp_mongo_db_), m_market_depth_history_db_codec_(m_sp_mongo_db_),
	m_last_barter_history_db_codec_(m_sp_mongo_db_), mr_top_of_book_web_socket_server_(r_top_of_book_websocket_server),
	mr_last_barter_web_socket_server_(r_last_barter_websocket_server),
	mr_market_depth_web_socket_server_(r_market_depth_websocket_server) {
		m_last_barter_history_db_codec_.get_all_data_from_collection(m_last_barter_collection_);
		m_market_depth_history_db_codec_.get_all_data_from_collection(m_market_depth_history_collection_);
	}

	std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
	FluxCppCore::MongoDBCodec<mobile_book::TopOfBook, mobile_book::TopOfBookList> m_top_of_book_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::MarketDepth, mobile_book::MarketDepthList> m_market_depth_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::LastBarter, mobile_book::LastBarterList> m_last_barter_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::RawMarketDepthHistory, mobile_book::RawMarketDepthHistoryList>
		m_market_depth_history_db_codec_;
	FluxCppCore::MongoDBCodec<mobile_book::RawLastBarterHistory, mobile_book::RawLastBarterHistoryList>
		m_last_barter_history_db_codec_;
	mobile_book_handler::MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook> &mr_top_of_book_web_socket_server_;
	mobile_book_handler::MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> &mr_last_barter_web_socket_server_;
	mobile_book_handler::MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> &mr_market_depth_web_socket_server_;
	mobile_book::RawLastBarterHistoryList m_last_barter_collection_;
	mobile_book::RawMarketDepthHistoryList m_market_depth_history_collection_;
};


class MobileBookConsumer : public MobileBookInterface {
public:
	explicit MobileBookConsumer(std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db,
	mobile_book_handler::MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook> &r_top_of_book_websocket_server,
	mobile_book_handler::MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> &r_last_barter_websocket_server,
	mobile_book_handler::MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> &r_market_depth_websocket_server) :
	MobileBookInterface(std::move(sp_mongo_db), r_top_of_book_websocket_server, r_last_barter_websocket_server,
		r_market_depth_websocket_server) {

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

				std::string exch_time;
				std::string arrival_time;
				FluxCppCore::format_time(m_market_depth_history_collection_.raw_market_depth_history(
					market_depth_index).exch_time(), exch_time);
				FluxCppCore::format_time(m_market_depth_history_collection_.raw_market_depth_history(
					market_depth_index).arrival_time(), arrival_time);
				char side;
				if (m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).side() ==
					mobile_book::TickType::BID) {
					side = 'B';
					} else {
						side = 'A';
					}

				PyMktDepth mkt_depth{m_market_depth_history_collection_.raw_market_depth_history(
					market_depth_index).symbol_n_exch_id().symbol().c_str(), exch_time.c_str(),
					arrival_time.c_str(), side,
					m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).position(),
					static_cast<double>(m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).px()),
					m_market_depth_history_collection_.raw_market_depth_history(market_depth_index).qty(),
					"", false, 0.0, 0, 0.0};

				process_market_depth(mkt_depth);
				++market_depth_index;

			} else {

				// Replay last barter
				std::string exch_time;
				std::string arrival_time;
				FluxCppCore::format_time(m_last_barter_collection_.raw_last_barter_history(
					last_barter_index).exch_time(), exch_time);
				FluxCppCore::format_time(m_last_barter_collection_.raw_last_barter_history(
					last_barter_index).arrival_time(), arrival_time);

				PyLastBarter last_barter{{m_last_barter_collection_.raw_last_barter_history(
					last_barter_index).symbol_n_exch_id().symbol().c_str(),
					m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).symbol_n_exch_id().exch_id().c_str()}, exch_time.c_str(),
					arrival_time.c_str(), static_cast<double>(
						m_last_barter_collection_.raw_last_barter_history(last_barter_index).px()),
					m_last_barter_collection_.raw_last_barter_history(last_barter_index).qty(),
					m_last_barter_collection_.raw_last_barter_history(last_barter_index).premium(),
					{m_last_barter_collection_.raw_last_barter_history(
						last_barter_index).market_barter_volume().id().c_str(),
						m_last_barter_collection_.raw_last_barter_history(
							last_barter_index).market_barter_volume().participation_period_last_barter_qty_sum(),
						m_last_barter_collection_.raw_last_barter_history(
							last_barter_index).market_barter_volume().applicable_period_seconds()}};

				process_last_barter(last_barter);

				++last_barter_index;
			}
		}
	}

	void process_market_depth(const PyMktDepth &md) {
		mon_md.push({1, md.symbol_, md.exch_time_, md.arrival_time_, md.side_, md.position_,
			md.px_, md.qty_, md.market_maker_, md.is_smart_depth_, md.cumulative_notional_,
			md.cumulative_qty_, md.cumulative_avg_px_});
		mkt_depth_fp(&md);
	}

	void process_last_barter(const PyLastBarter &e) {
		mon_lt.push({1, e.symbol_n_exch_id_.symbol_, e.symbol_n_exch_id_.exch_id_, e.exch_time_,
			e.arrival_time_, e.px_, e.qty_, e.premium_, e.market_barter_volume_.market_barter_volume_id_,
			e.market_barter_volume_.participation_period_last_barter_qty_sum_,
			e.market_barter_volume_.applicable_period_seconds_});
		last_barter_fp(&e);
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
				market_depth.set_id(1);
				market_depth.set_symbol(md.symbol_);
				auto time = FluxCppCore::parse_time(md.exch_time_);
				market_depth.set_exch_time(time);
				market_depth.set_arrival_time(time);
				market_depth.set_px(static_cast<float>(md.px_));
				market_depth.set_qty(md.qty_);
				if (md.side_ == 'B') {
					market_depth.set_side(mobile_book::TickType::BID);
				} else {
					market_depth.set_side(mobile_book::TickType::ASK);
				}
				market_depth.set_position(md.position_);

				if (md.position_ == 0) {
					top_of_book.set_id(1);
					top_of_book.set_symbol(md.symbol_);
					top_of_book.set_last_update_date_time(time);
					if (md.side_ == 'B') {
						top_of_book.mutable_bid_quote()->set_px(static_cast<float>(md.px_));
						top_of_book.mutable_bid_quote()->set_qty(md.qty_);
						top_of_book.mutable_bid_quote()->set_last_update_date_time(time);
					} else {
						top_of_book.mutable_ask_quote()->set_px(static_cast<float>(md.px_));
						top_of_book.mutable_ask_quote()->set_qty(md.qty_);
						top_of_book.mutable_ask_quote()->set_last_update_date_time(time);
					}

					auto tob_db_id = m_top_of_book_db_codec_.insert_or_update(top_of_book);
					top_of_book.set_id(tob_db_id);
					mr_top_of_book_web_socket_server_.NewClientCallBack(top_of_book, -1);
				}
				[[maybe_unused]] auto db_id = m_market_depth_db_codec_.insert_or_update(market_depth);
				market_depth.set_id(db_id);
				mr_market_depth_web_socket_server_.NewClientCallBack(market_depth, -1);
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
				last_barter.set_id(1);
				last_barter.mutable_symbol_n_exch_id()->set_symbol(lt.symbol_n_exch_id_.sym_);
				last_barter.mutable_symbol_n_exch_id()->set_exch_id(lt.symbol_n_exch_id_.exch_id_);
				last_barter.set_px(static_cast<float>(lt.px_));
				last_barter.set_qty(lt.qty_);
				auto time = FluxCppCore::parse_time(lt.exch_time_);
				last_barter.set_exch_time(time);
				last_barter.set_arrival_time(time);
				last_barter.mutable_market_barter_volume()->set_id(lt.market_barter_volume_.market_barter_volume_id_);
				last_barter.mutable_market_barter_volume()->set_participation_period_last_barter_qty_sum(
					lt.market_barter_volume_.participation_period_last_barter_qty_sum_);
				last_barter.mutable_market_barter_volume()->set_applicable_period_seconds(
					lt.market_barter_volume_.applicable_period_seconds_);

				tob.set_id(1);
				tob.set_symbol(lt.symbol_n_exch_id_.sym_);
				tob.mutable_last_barter()->set_px(static_cast<float>(lt.px_));
				tob.mutable_last_barter()->set_qty(lt.qty_);
				tob.mutable_last_barter()->set_last_update_date_time(last_barter.exch_time());
				tob.set_last_update_date_time(last_barter.exch_time());
				tob.add_market_barter_volume()->CopyFrom(last_barter.market_barter_volume());
				auto db_id = m_top_of_book_db_codec_.insert_or_update(tob);
				tob.set_id(db_id);
				mr_top_of_book_web_socket_server_.NewClientCallBack(tob, -1);
				db_id  = m_last_barter_db_codec_.insert(last_barter);
				last_barter.set_id(db_id);
				mr_last_barter_web_socket_server_.NewClientCallBack(last_barter, -1);
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
