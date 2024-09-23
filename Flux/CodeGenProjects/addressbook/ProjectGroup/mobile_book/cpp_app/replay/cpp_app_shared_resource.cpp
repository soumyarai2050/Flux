#include "cpp_app_shared_resource.h"

namespace mobile_book_handler {
    int32_t tob_ws_port = FluxCppCore::find_free_port();
    int32_t md_ws_port = FluxCppCore::find_free_port();
    int32_t lt_ws_port = FluxCppCore::find_free_port();
    mobile_book::TopOfBook top_of_book_obj;
    mobile_book::LastBarter last_barter_obj;
    mobile_book::MarketDepth market_depth_obj;
    const std::chrono::seconds TIME_OUT_CONNECTION = std::chrono::seconds(mobile_book_handler::connection_timeout);
    std::atomic<bool> shutdown_db_n_ws_thread{false};
    void signal_handler([[maybe_unused]] int signal) {
        shutdown_db_n_ws_thread = false;
    }

    extern "C" int32_t get_tob_ws_port() {
        return tob_ws_port;
    }

    extern "C" int32_t get_md_ws_port() {
        return md_ws_port;
    }

    extern "C" int32_t get_lt_ws_port() {
        return lt_ws_port;
    }

    last_barter_fp_t last_barter_fp{nullptr};
    mkt_depth_fp_t mkt_depth_fp{nullptr};

    extern "C" void register_last_barter_fp(last_barter_fp_t fcb) {
        last_barter_fp = fcb;
    }

    extern "C" void register_mkt_depth_fp(mkt_depth_fp_t mdfp) {
        mkt_depth_fp = mdfp;
    }

    extern "C" void register_last_barter_and_mkt_depth_fp(last_barter_fp_t fcb, mkt_depth_fp_t mdfp) {
        last_barter_fp = fcb;
        mkt_depth_fp = mdfp;
    }
}
