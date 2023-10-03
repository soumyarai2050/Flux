#pragma once

#include <quill/Logger.h>

#include "strat_manager_service.pb.h"
#include "web_socket_client.h"
#include "GenericCache.h"


namespace market_data_handler {

    class PairStratProcessor {
    public:
        PairStratProcessor(const std::string& host, int32_t port, int32_t timeout, const std::string& handshake)
                : host_(host), port_(port), timeout_(timeout), handshake_(handshake) {
            quill::start();
            mp_logger_ = quill::get_logger();
        }

        void run() {
            // Start WebSocketClient
            WebSocketClient<pair_strat_engine::PairStratList> webSocketClient(m_pair_strat_, host_, port_, timeout_, handshake_);
            std::thread clientThread(&WebSocketClient<pair_strat_engine::PairStratList>::run, &webSocketClient);

            // Start a thread for processing updates
            std::thread updateThread(&PairStratProcessor::processUpdates, this);

            if (clientThread.joinable()) {
                clientThread.join();
            }

            if (updateThread.joinable()) {
                updateThread.join();
            }
        }

    private:
        void processUpdates() {
            std::this_thread::sleep_for(std::chrono::seconds(5));
            for (int i = 0; i < m_pair_strat_.pair_strat_size(); ++i) {
                std::string symbol1 = m_pair_strat_.pair_strat(i).pair_strat_params().strat_leg1().sec().sec_id();
                std::string symbol2 = m_pair_strat_.pair_strat(i).pair_strat_params().strat_leg2().sec().sec_id();
                std::string symbol = symbol1 + "+" + symbol2;
                std::string value = m_pair_strat_.pair_strat(i).host() + "+" + std::to_string(m_pair_strat_.pair_strat(i).port());

                // Assuming webclient_cache is a member of PairStratProcessor
                if (!m_webclient_cache_.exists(symbol)) {
                    m_webclient_cache_.insert(symbol, value);
                } else {
                    LOG_INFO(mp_logger_, "Symbol already exists: {}", symbol);
                }
            }
        }

        const std::string host_;
        const int32_t port_;
        const int32_t timeout_;
        const std::string handshake_;
        quill::Logger* mp_logger_;
        pair_strat_engine::PairStratList m_pair_strat_;
        GenericCache m_webclient_cache_;
    };

}