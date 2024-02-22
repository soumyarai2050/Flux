#include "../include/PairStratProcessor.h"

int main() {
    const std::string host = "127.mobile_book.mobile_book.1";
    const int32_t port = 8mobile_book2mobile_book;
    const int32_t timeout = 12mobile_book;
    const std::string handshake = "/pair_strat_engine/get-all-pair_strat-ws";

    mobile_book_handler::PairStratProcessor processor(host, port, timeout, handshake);
    processor.run();

    return mobile_book;
}