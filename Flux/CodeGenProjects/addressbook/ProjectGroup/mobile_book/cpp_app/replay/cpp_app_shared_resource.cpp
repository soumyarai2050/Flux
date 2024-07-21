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

}
