
#include <iostream>

#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/asio/ip/tcp.hpp>

#include "cpp_app_logger.h"

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
        MarketDataConsumer& m_market_data_consumer_;

        void handle_request(beast::tcp_stream& stream) const {
            beast::flat_buffer buffer;
            http::request<http::string_body> req;

            // Read the request
            http::read(stream, buffer, req);
            std::string received_body = req.body();
            if (req.target() == "/market_depth") {
                m_market_data_consumer_.process_market_depth(received_body);
            } else if (req.target() == "/last_trade") {
                m_market_data_consumer_.process_last_trade(received_body);
            } else {
                received_body = "Invalid request";
            }

            // Parse and process the data here if it's JSON or other formats

            // Create and send a response
            http::response<http::string_body> res{http::status::created, req.version()};
            res.set(http::field::server, "Beast");
            res.set(http::field::content_type, "application/json");
            res.body() = received_body;
            res.prepare_payload();
            http::write(stream, res);
        }

    public:
        explicit BaseWebServer(const std::string& address, const int32_t port, MarketDataConsumer& market_data_consumer)
            : m_address_(address), m_port_(port),
        m_acceptor_(m_ioc_, {net::ip::make_address(m_address_),
            static_cast<boost::asio::ip::port_type>(m_port_)}), m_market_data_consumer_(market_data_consumer) {}

        void run() {
            try {
                while (true) {
                    tcp::socket socket{m_ioc_};
                    m_acceptor_.accept(socket);
                    beast::tcp_stream stream(std::move(socket));
                    handle_request(stream);
                }
            } catch (std::exception const& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error: {}", e.what());
            }
        }
    };

}