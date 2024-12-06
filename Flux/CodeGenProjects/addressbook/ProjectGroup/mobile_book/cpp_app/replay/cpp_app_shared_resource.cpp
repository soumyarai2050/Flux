#include "cpp_app_shared_resource.h"

#include <atomic>


std::unique_ptr<MobileBookConsumer> mobile_book_consumer = nullptr;
std::atomic<bool> shutdown_db_n_ws_thread{false};
extern "C" void signal_handler([[maybe_unused]] int signal) {
    mobile_book_consumer->cleanup();
    shutdown_db_n_ws_thread.store(true);
    shutdown_db_n_ws_thread.notify_all();
}