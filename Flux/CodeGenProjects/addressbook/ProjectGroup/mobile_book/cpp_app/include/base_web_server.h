#pragma once

#include <atomic>
#include <thread>
#include <chrono>

#include <boost/asio/steady_timer.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/asio/ip/tcp.hpp>

#include "cpp_app_logger.h"
#include "../replay/mobile_book_consumer.h"

namespace beast = boost::beast;
namespace http = beast::http;
namespace net = boost::asio;
using tcp = net::ip::tcp;

namespace FluxCppCore {
    class BaseWebServer {
    protected:
        const std::string m_address_;
        int32_t m_port_;
        net::io_context m_ioc_;
        tcp::acceptor m_acceptor_;
        MobileBookConsumer& m_mobile_book_consumer_;
        std::atomic<bool> stop_accepting_{false};
        boost::asio::steady_timer timer_;

        void reset_timer() {
            timer_.expires_after(std::chrono::seconds(mobile_book_handler::connection_timeout));
            timer_.async_wait([this](const boost::system::error_code& ec) {
                if (!ec) {
                    stop_accepting_ = true;
                    m_acceptor_.close(); // Close the acceptor to stop further accepts
                }
            });
        }

        void handle_request(beast::tcp_stream& stream) const {
            beast::flat_buffer buffer;
            http::request<http::string_body> req;

            // Read the request
            http::read(stream, buffer, req);
            std::string received_body = req.body();
            if (req.target() == "/market_depth") {
                m_mobile_book_consumer_.process_market_depth(received_body);
            } else if (req.target() == "/last_barter") {
                m_mobile_book_consumer_.process_last_barter(received_body);
            } else {
                received_body = "Invalid request";
            }

            // Create and send a response
            http::response<http::string_body> res{http::status::created, req.version()};
            res.set(http::field::server, "Beast");
            res.set(http::field::content_type, "application/json");
            res.body() = received_body;
            res.prepare_payload();
            http::write(stream, res);
        }

        void do_accept() {
            if (stop_accepting_) {
                return; // Stop accepting new connections
            }

            m_acceptor_.async_accept(
                [this](boost::system::error_code ec, tcp::socket socket) {
                    if (!ec) {
                        reset_timer(); // Reset the timer upon successful connection
                        beast::tcp_stream stream(std::move(socket));
                        handle_request(stream);
                    }
                    do_accept(); // Continue accepting the next connection
                });
        }

    public:
        explicit BaseWebServer(const std::string& address, const int32_t port, MobileBookConsumer& mobile_book_consumer)
            : m_address_(address), m_port_(port),
              m_acceptor_(m_ioc_, {net::ip::make_address(m_address_),
                                   static_cast<boost::asio::ip::port_type>(m_port_)}),
              m_mobile_book_consumer_(mobile_book_consumer),
              timer_(m_ioc_) {}

        void run() {
            try {
                reset_timer();

                // Start accepting connections asynchronously
                do_accept();

                // Run the IO context
                m_ioc_.run();
            } catch (std::exception const& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error: {}", e.what());
            }
        }

        void cleanup() {
            m_ioc_.stop();
        }

    };
}
