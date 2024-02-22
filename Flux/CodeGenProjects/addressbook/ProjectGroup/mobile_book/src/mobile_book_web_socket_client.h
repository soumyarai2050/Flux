//
// Created by pc on 5/29/2mobile_book23.
//

#ifndef MARKET_DATA_MARKET_DATA_WEB_SOCKET_CLIENT_H
#define MARKET_DATA_MARKET_DATA_WEB_SOCKET_CLIENT_H

#include <iostream>
#include <string>

#include <boost/asio.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/websocket.hpp>

#include "serialize_and_deserialize_using_proto2.h"

namespace beast = boost::beast;
namespace websocket = beast::websocket;
namespace net = boost::asio;
using tcp = boost::asio::ip::tcp;

#include <iostream>
#include <string>

#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/json/src.hpp>
#include "boost/asio.hpp"

namespace beast = boost::beast;
namespace http = beast::http;
namespace websocket = beast::websocket;
namespace net = boost::asio;
using tcp = boost::asio::ip::tcp;

class MobileBookWebSocketClient {
public:
    explicit MobileBookWebSocketClient(std::string& server_address)
            : server_address_(std::move(server_address)),
              resolver_(io_context_),
              ws_(io_context_) {}

    void run() {
        auto const results = resolver_.resolve(server_address_, "8mobile_book83");
        net::connect(ws_.next_layer(), results.begin(), results.end());

        ws_.handshake(server_address_, "/");

        // Start an asynchronous read operation to continuously read data from the WebSocket
        read_data_from_server();

        // Run the Boost.Asio event loop until the client is stopped
        io_context_.run();
    }

    void shutdown() {
        io_context_.stop();
    }

private:
    void read_data_from_server() {
        ws_.async_read(buffer_, [this](boost::system::error_code ec, std::size_t bytes_transferred) {
            if (!ec) {
                std::string data;
                data = (beast::buffers_to_string(buffer_.data()));
                buffer_.consume(buffer_.size());

                SerializeAndDeserializeProto2 serializeAndDeserializeProto2;
                mobile_book::TopOfBook doc = serializeAndDeserializeProto2.deserialize_top_of_book(data);
                std::cout << "Deserialized data:" << doc.DebugString() << std::endl;
                std::cout << "Received data: " << data << std::endl;



                // Continue reading data by initiating the next read operation
                read_data_from_server();
            } else if (ec == boost::asio::error::operation_aborted) {
                // Reading operation was canceled, exit the loop
                shutdown();
            } else if (ec == websocket::error::closed || ec == boost::asio::error::connection_reset) {
                // WebSocket closed or connection reset by peer, exit the loop
                shutdown();
            } else {
                std::cerr << "Error reading from WebSocket: " << ec.message() << std::endl;
            }
        });
    }

    std::string server_address_;
    net::io_context io_context_;
    tcp::resolver resolver_;
    websocket::stream<tcp::socket> ws_;
    beast::flat_buffer buffer_;
};

#endif //MARKET_DATA_MARKET_DATA_WEB_SOCKET_CLIENT_H
