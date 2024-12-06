#pragma once

#include <atomic>
#include <memory>

#include "mobile_book_consumer.h"


extern std::unique_ptr<MobileBookConsumer> mobile_book_consumer;
extern std::atomic<bool> shutdown_db_n_ws_thread;
extern "C" void signal_handler([[maybe_unused]] int signal);

