#pragma once

#include <quill/Logger.h>

#include "email_book_service.pb.h"
#include "web_socket_client.h"
#include "GenericCache.h"


namespace mobile_book_handler {

    class SubscriptionDataParser {
    public:
        explicit SubscriptionDataParser(quill::Logger* logger = quill::get_logger()) : mp_logger_(logger) {
            // Read the SUBSCRIPTION_DATA environment variable
            const char* m_subscription_data_c_str = std::getenv("SUBSCRIPTION_DATA");
            if (m_subscription_data_c_str) {
                std::string m_subscription_data_str(m_subscription_data_c_str);
                parse_subscription_data(m_subscription_data_str);
            } else {
                LOG_ERROR(mp_logger_, "SUBSCRIPTION_DATA environment variable is not set." );
            }
        }

        void get_subscription_data(std::vector<std::pair<std::string, std::string>> &r_subscription_data) const {
            r_subscription_data = m_subscription_data_vector_;
        }

    protected:
        quill::Logger* mp_logger_;
        std::vector<std::pair<std::string, std::string>> m_subscription_data_vector_;

        void parse_subscription_data(const std::string& r_data_str) {
            std::istringstream ss(r_data_str);
            std::string symbol, product_type, token;

            int index = 0;
            while (std::getline(ss, token, ',')) {
                if (index % 2 == 0) {
                    symbol = token;
                } else {
                    product_type = token;
                    m_subscription_data_vector_.emplace_back(symbol, product_type);
                }
                index++;
            }
        }
    };

    class PairStratProcessor {
    public:
        PairStratProcessor(const std::string& kr_host, int32_t port, int32_t timeout, const std::string& kr_handshake)
                : km_host_(kr_host), km_port_(port), km_timeout_(timeout), km_handshake_(kr_handshake) {
            quill::start();
            mp_logger_ = quill::get_logger();
        }

        void run() {
            // Start WebSocketClient
            WebSocketClient<phone_book::PairStratList> webSocketClient(m_pair_strat_, km_host_, km_port_, km_timeout_, km_handshake_);
            std::thread clientThread(&WebSocketClient<phone_book::PairStratList>::run, &webSocketClient);

            // Start a thread for processing updates
            std::thread updateThread(&PairStratProcessor::processUpdates, this);

            if (clientThread.joinable()) {
                clientThread.join();
            }

            if (updateThread.joinable()) {
                updateThread.join();
            }
        }

    protected:
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

        const std::string km_host_;
        const int32_t km_port_;
        const int32_t km_timeout_;
        const std::string km_handshake_;
        quill::Logger* mp_logger_;
        phone_book::PairStratList m_pair_strat_;
        GenericCache m_webclient_cache_;
    };

}