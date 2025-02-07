#include "../include/PairPlanProcessor.h"

int main() {
    const std::string host = "127.0.0.1";
    const int32_t port = 8020;
    const int32_t timeout = 120;
    const std::string handshake = "/phone_book/get-all-pair_plan-ws";

    mobile_book_handler::PairPlanProcessor processor(host, port, timeout, handshake);
    processor.run();

    return 0;
}