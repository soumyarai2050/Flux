#pragma once

#include <chrono>

#include "mobile_book_service.pb.h"
#include "mobile_book_cache.h"
#include "utility_functions.h"

namespace mobile_book_handler {
    extern int32_t tob_ws_port;
    extern int32_t md_ws_port;
    extern int32_t lt_ws_port;
    extern mobile_book::TopOfBook top_of_book_obj;
    extern mobile_book::LastBarter last_barter_obj;
    extern mobile_book::MarketDepth market_depth_obj;
    extern const std::chrono::seconds TIME_OUT_CONNECTION;

}
