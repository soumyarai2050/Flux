//
// Created by pc on 9/23/2023.
//

#include "strat_manager_service.pb.h"
#include "web_socket_client.h"

void processUpdates(pair_strat_engine::PairStratList& pairStrat, std::unordered_map<std::string, std::string>& webclient_cache, quill::Logger* logger) {
    std::this_thread::sleep_for(std::chrono::seconds(5));
    LOG_INFO(logger, "Processing updates. Current pairStrat size: {}", pairStrat.pair_strat_size());
    for (int i = 0; i < pairStrat.pair_strat_size(); ++i) {
        std::string symbol = pairStrat.pair_strat(i).pair_strat_params().strat_leg1().sec().sec_id();
        std::string host_ = pairStrat.pair_strat(i).host();
        std::string port_ = std::to_string(pairStrat.pair_strat(i).port());
        auto found = webclient_cache.find(symbol);
        if (found == webclient_cache.end()) {
            webclient_cache[symbol] = host_ + "+" + port_;
        } else {
            LOG_INFO(logger, "Symbol already exists: {}", symbol);
        }
    }

    for (const auto& pair : webclient_cache) {
        std::cout << "Key: " << pair.first << ", Value: " << pair.second << std::endl;
    }
}

int main() {
    quill::start();
    pair_strat_engine::PairStratList pairStrat;
    quill::Logger* logger = quill::get_logger();
    std::unordered_map<std::string, std::string> webclient_cache;
    const std::string host = "127.0.0.1";
    const int32_t port = 8020;
    const int32_t timeout = 120;
    const std::string handshake = "/pair_strat_engine/get-all-pair_strat-ws";
    WebSocketClient<pair_strat_engine::PairStratList> webSocketClient(pairStrat, host, port, timeout, handshake);

    std::thread clientThread(&WebSocketClient<pair_strat_engine::PairStratList>::run, &webSocketClient);

    // Start a thread for processing updates
    std::thread updateThread(processUpdates, std::ref(pairStrat), std::ref(webclient_cache), logger);

    if (clientThread.joinable()) {
        clientThread.join();
    }

    if (updateThread.joinable()) {
        updateThread.join();
    }

    return 0;
}