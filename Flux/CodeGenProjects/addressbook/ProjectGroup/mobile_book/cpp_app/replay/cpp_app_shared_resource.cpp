#include "cpp_app_shared_resource.h"

#include <cstdlib>


std::atomic<bool> shutdown_db_n_ws_thread{false};
void signal_handler(int signal) {
    shutdown_db_n_ws_thread.store(true);
    exit(signal);
}