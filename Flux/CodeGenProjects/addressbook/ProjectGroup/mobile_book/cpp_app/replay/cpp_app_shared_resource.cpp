#include "cpp_app_shared_resource.h"


std::atomic<bool> shutdown_db_n_ws_thread{false};
void signal_handler([[maybe_unused]] int signal) {
    shutdown_db_n_ws_thread = false;
}