#pragma once

#include <atomic>



extern std::atomic<bool> shutdown_db_n_ws_thread;
void signal_handler([[maybe_unused]] int signal);

