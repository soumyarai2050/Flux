# pragma once

#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/json/src.hpp>
#include "boost/asio.hpp"

#include "MD_DepthSingleSide.h"

namespace beast = boost::beast;
namespace http = beast::http;
namespace websocket = beast::websocket;
namespace net = boost::asio;
using tcp = boost::asio::ip::tcp;

class WebSocketServer {
public:
    WebSocketServer() : acceptor_(io_context_, tcp::endpoint{tcp::v4(), 8083}), timer_(io_context_, boost::posix_time::seconds(60)) {}

    void run() {
        std::shared_ptr socket = std::make_shared<tcp::socket>(io_context_);
        acceptor_.async_accept(*socket, [&](const boost::system::error_code &ec) {
            timer_.cancel(); // cancel the timer when a connection is accepted
            if (!ec) {
                session(std::move(*socket));
                // Create a new socket object to be used for the next connection
                socket = std::make_shared<tcp::socket>(io_context_);
            } else if (ec != boost::asio::error::operation_aborted) {
                std::cerr << "Error accepting connection: " << ec.message() << std::endl;
            }
            timer_.expires_from_now(boost::posix_time::seconds(60)); // reset the timer
            run();
        });

        timer_.async_wait([&](boost::system::error_code ec) {
            if (!ec) {
                Shutdown();
                std::cout << "Timeout reached" << std::endl;
                if(shutdown)
                    io_context_.stop();
                else
                    io_context_.run();

            } else if (ec != boost::asio::error::operation_aborted) {
                std::cerr << "Error accepting connection: " << ec.message() << std::endl;
            }
        });

        io_context_.run();
    }

    ~WebSocketServer(){
        shutdown = true;
        ws_vector.clear();
    }

    void publish(const std::string& send_string)
    {
        for(auto &ws_ptr: ws_vector){
            ws_ptr->write(net::buffer(send_string));
        }
    }

    void Shutdown(){
        shutdown = true;
    }

private:
    auto get_market_depth_snapshot_json() {

        net::io_context ioc;
        tcp::resolver resolver{ioc};
        auto const results = resolver.resolve(host_, port_);

        tcp::socket http_socket{ioc};
        net::connect(http_socket, results.begin(), results.end());

        http::request<http::string_body> request{http::verb::get, target_, 11};
        request.set(http::field::host, host_ + ":" + port_);
        request.set(http::field::user_agent, BOOST_BEAST_VERSION_STRING);

        http::write(http_socket, request);

        beast::flat_buffer buffer;
        http::response<http::dynamic_body> response;
        http::read(http_socket, buffer, response);

        return boost::json::parse(beast::buffers_to_string(response.body().data()));
    }

    void session(tcp::socket socket) {
        try {
            std::shared_ptr<websocket::stream<tcp::socket>> ws_ptr = std::make_shared<websocket::stream<tcp::socket>>(std::move(socket));
            try {
                ws_ptr->accept();
            }
            catch (std::exception const& e){
                std::cerr << "accept" << e.what() << std::endl;
            }
            auto json_obj = get_market_depth_snapshot_json();

            std::string body_str(std::move(boost::json::serialize(json_obj)));

            // Send the HTTP response body to the WebSocket client
            ws_ptr->write(net::buffer(body_str));
            ws_vector.push_back(std::move(ws_ptr));
        }
        catch (std::exception const& e) {
            std::cerr << "session: " << e.what() << std::endl;
        }
    }

    std::vector<std::shared_ptr<websocket::stream<tcp::socket>>> ws_vector;
    std::vector <std::thread> ws_client_threads;
    bool shutdown = false;
    net::io_context io_context_;
    tcp::acceptor acceptor_;
    boost::asio::deadline_timer timer_;
    std::string host_ = "127.0.0.1";
    std::string port_ = "8040";
    std::string target_ = "/market_data/get-all-market_depth";
    int num_connections_ = 0;
};
