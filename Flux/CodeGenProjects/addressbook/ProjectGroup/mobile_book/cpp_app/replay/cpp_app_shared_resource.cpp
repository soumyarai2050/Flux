#include "cpp_app_shared_resource.h"

#include <atomic>


std::unique_ptr<MobileBookConsumer> mobile_book_consumer = nullptr;
std::atomic<bool> keepRunning{true};
extern "C" void signal_handler([[maybe_unused]] int signal) {
    mobile_book_consumer->cleanup();
    keepRunning.store(false);
}