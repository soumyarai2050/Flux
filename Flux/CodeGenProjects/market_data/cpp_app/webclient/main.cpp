#include "../include/PairStratProcessor.h"

int main() {
    const std::string host = "127.0.0.1";
    const int32_t port = 8020;
    const int32_t timeout = 120;
    const std::string handshake = "/pair_strat_engine/get-all-pair_strat-ws";

    market_data_handler::PairStratProcessor processor(host, port, timeout, handshake);
    processor.run();

    return 0;
}