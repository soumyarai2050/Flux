#pragma once

#include "mobile_book_service_shared_data_structure.h"
#include "mobile_book_service.h"
#include "boost/json.hpp"

class MobileBookPublisherInterface {
public:
  virtual ~MobileBookPublisherInterface() = default;

  virtual void process_market_depth(const MarketDepthQueueElement& r_market_depth_queue_element) = 0;
  virtual void process_last_barter(const LastBarterQueueElement& kr_last_barter_queue_element) = 0;
  virtual void process_market_depth(const MarketDepth& kr_market_depth) = 0;

  virtual void process_last_barter(const LastBarter& kr_last_barter) {}

  virtual int32_t get_last_barter_next_inserted_id() = 0;
  virtual bool get_top_of_book(TopOfBook& r_top_of_book, const int32_t k_top_of_book_id) = 0;
  virtual void get_top_of_book(TopOfBookList& r_top_of_book_list, const int32_t limit) = 0;
  virtual int32_t get_next_insert_id_market_depth() = 0;
  virtual int32_t insert_market_depth(MarketDepth& r_market_depth) = 0;
  virtual bool get_market_depth(MarketDepth& r_market_depth, const int32_t market_depth_id) = 0;
  virtual void get_market_depth(MarketDepthList& r_market_depth_list, const int32_t limit) = 0;
  virtual bool patch_market_depth(const MarketDepth& r_market_depth) = 0;
  virtual bool patch_market_depth(const int64_t id, const boost::json::object& kr_market_depth_json) = 0;
  virtual bool delete_market_depth(const int market_depth_id) = 0;
  virtual bool delete_market_depth() = 0;
  virtual bool get_last_barter(LastBarter& r_last_barter, const int32_t k_last_barter_id) = 0;
  virtual bool get_last_barter(LastBarterList& r_last_barter_list, const int32_t limit) = 0;
  virtual bool delete_last_barter(const int32_t k_last_barter_id) = 0;
  virtual bool delete_last_barter() = 0;
};
