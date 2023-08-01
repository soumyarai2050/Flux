//
// Created by pc on 5/28/2023.
//

#ifndef MARKET_DATA_MARKET_DATA_WEB_SOCKET_SERVER_H
#define MARKET_DATA_MARKET_DATA_WEB_SOCKET_SERVER_H

#include <iostream>
#include <string>

#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/json/src.hpp>
#include "boost/asio.hpp"

#include "serialize_and_deserialize_using_proto2.h"

namespace beast = boost::beast;
namespace http = beast::http;
namespace websocket = beast::websocket;
namespace net = boost::asio;
using tcp = boost::asio::ip::tcp;

class MarketDataWebSocketServer {
public:
    MarketDataWebSocketServer() : acceptor_(io_context_, tcp::endpoint{tcp::v4(), 8083}) {}

    void run() {
        acceptor_.async_accept([this](boost::system::error_code ec, tcp::socket socket) {
            if (!ec) {
                session(std::move(socket));
            } else {
                std::cerr << "Error accepting connection: " << ec.message() << std::endl;
            }
            run();
        });

        io_context_.run();
    }

    void shutdown() {
        io_context_.stop();
    }

    ~MarketDataWebSocketServer(){
        ws_vector.clear();
    }

private:
    void session(tcp::socket socket) {
        try {
            std::shared_ptr<websocket::stream<tcp::socket>> ws_ptr =
                    std::make_shared<websocket::stream<tcp::socket>>(std::move(socket));

            ws_ptr->accept();

            SerializeAndDeserializeProto2 serializeAndDeserializeProto2;
            std::vector<market_data::TopOfBook> top_of_book = serializeAndDeserializeProto2.create_top_of_book();
            std::vector<std::string> serialized_data = serializeAndDeserializeProto2.serialize_top_of_book(top_of_book);

            for (auto& serialized_doc : serialized_data) {
                // Create a JSON array with a single element containing the serialized data
                std::string serialized_data_list = "[" + serialized_doc + "]";

                // Send the serialized data list to the WebSocket client
                ws_ptr->write(net::buffer(serialized_data_list));
                break;
            }

            for (auto& serialized_doc : serialized_data) {
                // Send the serialized data list to the WebSocket client
                ws_ptr->write(net::buffer(serialized_doc));
            }

            ws_vector.push_back(std::move(ws_ptr));
        } catch (std::exception const& e) {
            std::cerr << "session: " << e.what() << std::endl;
        }
    }

    std::vector<std::shared_ptr<websocket::stream<tcp::socket>>> ws_vector;
    net::io_context io_context_;
    tcp::acceptor acceptor_;
};

#endif //MARKET_DATA_MARKET_DATA_WEB_SOCKET_SERVER_H
