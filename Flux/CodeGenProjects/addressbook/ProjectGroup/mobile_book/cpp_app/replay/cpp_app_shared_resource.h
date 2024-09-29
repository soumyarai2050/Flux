#pragma once

#include <chrono>
#include <atomic>

#include "mobile_book_service.pb.h"
#include "mobile_book_web_socket_server.h"
#include "mobile_book_service_shared_data_structure.h"

namespace mobile_book_handler {

    extern std::atomic<bool> shutdown_db_n_ws_thread;
    void signal_handler([[maybe_unused]] int signal);

    using last_barter_fp_t = int(*)(PyLastBarter const*);


    using mkt_depth_fp_t = int(*)(PyMarketDepth const*);

    extern last_barter_fp_t last_barter_fp;
    extern mkt_depth_fp_t mkt_depth_fp;

    extern "C" void register_last_barter_fp(last_barter_fp_t fcb);

    extern "C" void register_mkt_depth_fp(mkt_depth_fp_t mdfp);

    extern "C" void register_last_barter_and_mkt_depth_fp(last_barter_fp_t fcb, mkt_depth_fp_t mdfp);

}
