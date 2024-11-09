#include "mobile_book_publisher.h"


void MobileBookPublisher::process_market_depth(const MarketDepthQueueElement &kr_market_depth_queue_element) {

	if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
		update_shm_cache(kr_market_depth_queue_element);
	}

	mobile_book::MarketDepth market_depth;

	market_depth.set_id(0);
	market_depth.set_symbol(kr_market_depth_queue_element.symbol_);
	market_depth.set_exch_time(kr_market_depth_queue_element.exch_time_);
	market_depth.set_arrival_time(kr_market_depth_queue_element.arrival_time_);
	if (kr_market_depth_queue_element.side_ == 'B') {
		market_depth.set_side(mobile_book::TickType::BID);
	} else if (kr_market_depth_queue_element.side_ == 'A') {
		market_depth.set_side(mobile_book::TickType::ASK);
	}
	if (kr_market_depth_queue_element.is_px_set_) {
		market_depth.set_px(static_cast<float>(kr_market_depth_queue_element.px_));
	}
	if (kr_market_depth_queue_element.is_qty_set_) {
		market_depth.set_qty(kr_market_depth_queue_element.qty_);
	}
	market_depth.set_position(kr_market_depth_queue_element.position_);
	if (kr_market_depth_queue_element.is_market_maker_set_) {
		market_depth.set_market_maker(kr_market_depth_queue_element.market_maker_);
	}
	if (kr_market_depth_queue_element.is_is_smart_depth_set_) {
		market_depth.set_is_smart_depth(kr_market_depth_queue_element.is_smart_depth_);
	}
	if (kr_market_depth_queue_element.is_cumulative_notional_set_) {
		market_depth.set_cumulative_notional(static_cast<float>(kr_market_depth_queue_element.cumulative_notional_));
	}
	if (kr_market_depth_queue_element.is_cumulative_qty_set_) {
		market_depth.set_cumulative_qty(kr_market_depth_queue_element.cumulative_qty_);
	}
	if (kr_market_depth_queue_element.is_cumulative_avg_px_set_) {
		market_depth.set_cumulative_avg_px(static_cast<float>(kr_market_depth_queue_element.cumulative_avg_px_));
	}

	if (mr_config_.m_market_depth_db_update_publish_policy_ == PublishPolicy::PRE) {
		create_or_update_market_depth_db(market_depth);
	}

	if (mr_config_.m_market_depth_http_update_publish_policy_ == PublishPolicy::PRE) {
		create_or_update_market_depth_http(market_depth);
	}

	if (mr_config_.m_market_depth_ws_update_publish_policy_ == PublishPolicy::PRE ) {
		publish_market_depth_over_ws(market_depth);
	}

	if (market_depth.position() == 0) {
		mobile_book::TopOfBook top_of_book;
		top_of_book.set_id(0);
		top_of_book.set_symbol(market_depth.symbol());
		top_of_book.set_last_update_date_time(market_depth.exch_time());
		if (market_depth.side() == mobile_book::TickType::BID) {
			top_of_book.mutable_bid_quote()->set_px(market_depth.px());
			top_of_book.mutable_bid_quote()->set_qty(market_depth.qty());
			top_of_book.mutable_bid_quote()->set_last_update_date_time(market_depth.exch_time());
		} else {
			top_of_book.mutable_ask_quote()->set_px(market_depth.px());
			top_of_book.mutable_ask_quote()->set_qty(market_depth.qty());
			top_of_book.mutable_ask_quote()->set_last_update_date_time(market_depth.exch_time());
		}

		if (mr_config_.m_top_of_book_db_update_publish_policy_ == PublishPolicy::PRE) {
			create_or_update_top_of_book_db(top_of_book);
		}

		if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::PRE) {
			create_or_update_top_of_book_http(top_of_book);
		}

		if (mr_config_.m_top_of_book_ws_update_publish_policy_ == PublishPolicy::PRE) {
			m_top_of_book_web_socket_server_.value().NewClientCallBack(top_of_book, -1);
		}
	}

	if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_market_depth_db_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_market_depth_http_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_market_depth_ws_update_publish_policy_ == PublishPolicy::POST) {

		mon_md.push(kr_market_depth_queue_element);
	}
}

void MobileBookPublisher::process_last_barter(const LastBarterQueueElement &kr_last_barter_queue_element) {

	if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::PRE) {
		update_shm_cache(kr_last_barter_queue_element);
	}

	mobile_book::LastBarter last_barter_data;

	last_barter_data.set_id(0);
	last_barter_data.mutable_symbol_n_exch_id()->set_symbol(kr_last_barter_queue_element.symbol_n_exch_id_.symbol_);
	last_barter_data.mutable_symbol_n_exch_id()->set_exch_id(kr_last_barter_queue_element.symbol_n_exch_id_.exch_id_);
	last_barter_data.set_exch_time(kr_last_barter_queue_element.exch_time_);
	last_barter_data.set_px(static_cast<float>(kr_last_barter_queue_element.px_));
	last_barter_data.set_qty(kr_last_barter_queue_element.qty_);
	if (kr_last_barter_queue_element.is_premium_set_) {
		last_barter_data.set_premium(static_cast<float>(kr_last_barter_queue_element.premium_));
	}
	if (kr_last_barter_queue_element.is_market_barter_volume_set_) {
		last_barter_data.mutable_market_barter_volume()->set_id(kr_last_barter_queue_element.market_barter_volume_.id_);

		if (kr_last_barter_queue_element.market_barter_volume_.is_applicable_period_seconds_set_) {
			last_barter_data.mutable_market_barter_volume()->set_applicable_period_seconds(
				kr_last_barter_queue_element.market_barter_volume_.applicable_period_seconds_);
		}

		if (kr_last_barter_queue_element.market_barter_volume_.is_participation_period_last_barter_qty_sum_set_) {
			last_barter_data.mutable_market_barter_volume()->set_participation_period_last_barter_qty_sum(
				kr_last_barter_queue_element.market_barter_volume_.participation_period_last_barter_qty_sum_);
		}
	}

	if (mr_config_.m_last_barter_db_update_publish_policy_ == PublishPolicy::PRE) {
		create_or_update_last_barter_db(last_barter_data);
	}

	if (mr_config_.m_last_barter_http_update_publish_policy_ == PublishPolicy::PRE) {
		create_or_update_last_barter_http(last_barter_data);
	}

	if (mr_config_.m_last_barter_ws_update_publish_policy_ == PublishPolicy::PRE) {
		publish_last_barter_over_ws(last_barter_data);
	}

	mobile_book::TopOfBook top_of_book;
	top_of_book.set_id(0);
	top_of_book.set_symbol(last_barter_data.symbol_n_exch_id().symbol());
	top_of_book.set_last_update_date_time(last_barter_data.exch_time());
	top_of_book.mutable_last_barter()->set_px(last_barter_data.px());
	top_of_book.mutable_last_barter()->set_qty(last_barter_data.qty());
	top_of_book.mutable_last_barter()->set_last_update_date_time(last_barter_data.exch_time());
	if (last_barter_data.has_premium()) {
		top_of_book.mutable_last_barter()->set_premium(last_barter_data.premium());
	}

	if (last_barter_data.has_market_barter_volume()) {
		top_of_book.add_market_barter_volume()->CopyFrom(last_barter_data.market_barter_volume());
	}

	if (mr_config_.m_top_of_book_db_update_publish_policy_ == PublishPolicy::PRE) {
		create_or_update_top_of_book_db(top_of_book);
	}

	if (mr_config_.m_top_of_book_http_update_publish_policy_ == PublishPolicy::PRE) {
		create_or_update_top_of_book_http(top_of_book);
	}

	if (mr_config_.m_top_of_book_ws_update_publish_policy_ == PublishPolicy::PRE) {
		m_top_of_book_web_socket_server_.value().NewClientCallBack(top_of_book, -1);
	}

	if (mr_config_.m_shm_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_last_barter_db_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_last_barter_http_update_publish_policy_ == PublishPolicy::POST ||
		mr_config_.m_last_barter_ws_update_publish_policy_ == PublishPolicy::POST) {

		mon_lt.push(kr_last_barter_queue_element);
	}
}

void MobileBookPublisher::update_shm_cache(const MarketDepthQueueElement& kr_market_depth_queue_element)  {

	if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_1_symbol_) {
		++m_shm_symbol_cache_.m_leg_1_data_shm_cache_.update_counter;
		update_market_depth_cache(kr_market_depth_queue_element,
			m_shm_symbol_cache_.m_leg_1_data_shm_cache_);
	}

	if (kr_market_depth_queue_element.symbol_ == mr_config_.m_leg_2_symbol_) {
		++m_shm_symbol_cache_.m_leg_2_data_shm_cache_.update_counter;
		update_market_depth_cache(kr_market_depth_queue_element,
			m_shm_symbol_cache_.m_leg_2_data_shm_cache_);
	}

	m_symbols_manager_.write_to_shared_memory(m_shm_symbol_cache_);
}

void MobileBookPublisher::update_shm_cache(const LastBarterQueueElement& kr_last_barter_queue_element) {
	if (kr_last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_1_symbol_) {
		++m_shm_symbol_cache_.m_leg_1_data_shm_cache_.update_counter;
		update_last_barter_cache(kr_last_barter_queue_element,
			m_shm_symbol_cache_.m_leg_1_data_shm_cache_);
	}

	if (kr_last_barter_queue_element.symbol_n_exch_id_.symbol_ == mr_config_.m_leg_2_symbol_) {
		++m_shm_symbol_cache_.m_leg_2_data_shm_cache_.update_counter;
		update_last_barter_cache(kr_last_barter_queue_element,
			m_shm_symbol_cache_.m_leg_2_data_shm_cache_);
	}

	m_symbols_manager_.write_to_shared_memory(m_shm_symbol_cache_);
}

void MobileBookPublisher::update_market_depth_cache(const MarketDepthQueueElement& kr_market_depth_queue_element,
	MobileBookShmCache& r_mobile_book_cache_out) {

	if (kr_market_depth_queue_element.side_ == 'B') {
		r_mobile_book_cache_out.bid_market_depths_[
			kr_market_depth_queue_element.position_] = kr_market_depth_queue_element;
	}

	if (kr_market_depth_queue_element.side_ == 'A') {
		r_mobile_book_cache_out.ask_market_depths_[kr_market_depth_queue_element.position_] = kr_market_depth_queue_element;
	}

	if (kr_market_depth_queue_element.position_ == 0) {
		FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.symbol_,
			kr_market_depth_queue_element.symbol_, sizeof(r_mobile_book_cache_out.top_of_book_.symbol_));
		FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.last_update_date_time_,
			kr_market_depth_queue_element.exch_time_, sizeof(
				r_mobile_book_cache_out.top_of_book_.last_update_date_time_));

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
			FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.bid_quote_.last_update_date_time_,
				kr_market_depth_queue_element.exch_time_,
				sizeof(r_mobile_book_cache_out.top_of_book_.bid_quote_.last_update_date_time_));
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
			FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.ask_quote_.last_update_date_time_,
				kr_market_depth_queue_element.exch_time_,
				sizeof(r_mobile_book_cache_out.top_of_book_.ask_quote_.last_update_date_time_));
			r_mobile_book_cache_out.top_of_book_.ask_quote_.is_last_update_date_time_set_ = true;
		}
	}
}

void MobileBookPublisher::update_last_barter_cache(const LastBarterQueueElement& kr_last_barter_queue_element,
	MobileBookShmCache& r_mobile_book_cache_out) {
	// LastBarter
		r_mobile_book_cache_out.last_barter_ = kr_last_barter_queue_element;

		// TopOfBook
		FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.symbol_,
			kr_last_barter_queue_element.symbol_n_exch_id_.symbol_, sizeof(r_mobile_book_cache_out.top_of_book_.symbol_));
		FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.last_update_date_time_,
			kr_last_barter_queue_element.exch_time_, sizeof(r_mobile_book_cache_out.top_of_book_.last_update_date_time_));

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
		FluxCppCore::StringUtil::setString(r_mobile_book_cache_out.top_of_book_.last_barter_.last_update_date_time_,
			kr_last_barter_queue_element.exch_time_,
			sizeof(r_mobile_book_cache_out.top_of_book_.last_barter_.last_update_date_time_));
		r_mobile_book_cache_out.top_of_book_.last_barter_.is_last_update_date_time_set_ = true;
}

void MobileBookPublisher::create_or_update_market_depth_db(mobile_book::MarketDepth &kr_market_depth) {
	m_market_depth_db_codec_.insert_or_update(kr_market_depth);
}

void MobileBookPublisher::create_or_update_top_of_book_db(mobile_book::TopOfBook &top_of_book) {
	auto db_id = m_top_of_book_db_codec_.insert_or_update(top_of_book);
	if (db_id != -1) {
		top_of_book.set_id(db_id);
	}
}

void MobileBookPublisher::create_or_update_last_barter_db(mobile_book::LastBarter &r_last_barter) {
	auto db_id = m_last_barter_db_codec_.insert(r_last_barter);
	r_last_barter.set_id(db_id);
}

void MobileBookPublisher::create_or_update_market_depth_http(mobile_book::MarketDepth &kr_market_depth) {
	auto db_id  = m_market_depth_db_codec_.get_db_id_from_root_model_obj(kr_market_depth);
	if (db_id == -1) {
		db_id = m_market_depth_db_codec_.get_max_id_from_collection();
		++db_id;
		kr_market_depth.set_id(db_id);
		assert(m_md_http_client_.value().create_client(kr_market_depth));
		if (mr_config_.m_market_depth_db_update_publish_policy_ == PublishPolicy::OFF) {
			m_market_depth_db_codec_.update_root_model_key_to_db_id(kr_market_depth);
		}
	} else {
		kr_market_depth.set_id(db_id);
		assert(m_md_http_client_.value().patch_client(kr_market_depth));
	}
}

void MobileBookPublisher::create_or_update_top_of_book_http(mobile_book::TopOfBook &r_top_of_book) {
	auto db_id = m_top_of_book_db_codec_.get_db_id_from_root_model_obj(r_top_of_book);
	if (db_id == -1) {
		db_id = m_top_of_book_db_codec_.get_max_id_from_collection();
		++db_id;
		r_top_of_book.set_id(db_id);
		assert(m_tob_web_client_.value().create_client(r_top_of_book));
		if (mr_config_.m_top_of_book_db_update_publish_policy_ == PublishPolicy::OFF) {
			m_top_of_book_db_codec_.update_root_model_key_to_db_id(r_top_of_book);
		}
	} else {
		r_top_of_book.set_id(db_id);
		assert(m_tob_web_client_.value().patch_client(r_top_of_book));
	}
}

void MobileBookPublisher::create_or_update_last_barter_http(mobile_book::LastBarter &r_last_barter) {
	assert(m_lt_web_client_.value().create_client(r_last_barter));
}

void MobileBookPublisher::publish_market_depth_over_ws(mobile_book::MarketDepth &kr_market_depth) {
	m_market_depth_web_socket_server_.value().NewClientCallBack(kr_market_depth, -1);
}

void MobileBookPublisher::publish_last_barter_over_ws(mobile_book::LastBarter &r_last_barter) {
	m_last_barter_web_socket_server_.value().NewClientCallBack(r_last_barter, -1);
}


