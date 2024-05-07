#pragma once

#include <chrono>

#include "mobile_book_service.pb.h"
#include "mobile_book_cache.h"
#include "utility_functions.h"

namespace mobile_book_handler {
    static int32_t tob_ws_port = FluxCppCore::find_free_port();
    static int32_t md_ws_port = FluxCppCore::find_free_port();
    static int32_t lt_ws_port = FluxCppCore::find_free_port();
    mobile_book::TopOfBook top_of_book_obj;
    mobile_book::LastBarter last_barter_obj;
    mobile_book::MarketDepth market_depth_obj;
    mobile_book_cache::MarketDepthCache market_DepthCache;
    mobile_book_cache::TopOfBookCache topOfBookCache_;
    mobile_book_cache::LastBarterCache lastBarterCache_;
    const std::chrono::seconds TIME_OUT_CONNECTION = std::chrono::seconds(36000);
}