#include "cpp_app_shared_resource.h"

namespace mobile_book_handler {

    std::atomic<bool> shutdown_db_n_ws_thread{false};
    void signal_handler([[maybe_unused]] int signal) {
        shutdown_db_n_ws_thread = false;
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
