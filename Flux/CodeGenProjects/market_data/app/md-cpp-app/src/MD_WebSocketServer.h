# pragma once

#include <iostream>
#include <string>
#include <thread>

#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/websocket.hpp>


namespace beast = boost::beast;
namespace http = beast::http;
namespace websocket = beast::websocket;
namespace net = boost::asio;
using tcp = boost::asio::ip::tcp;

class WebsocketServer {
public:
    explicit WebsocketServer(unsigned short port = 8083)
            : address_{net::ip::make_address("127.0.0.1")},
              port_{static_cast<unsigned short>(port)},
              ioc_{1},
              acceptor_{ioc_, {address_, port_}} {}


    [[noreturn]] void run() {
        rapidjson::Document prev_data;
        rapidjson::Document market_depth_snapshot_json_data;

        while (true) {
            tcp::socket socket{ioc_};
            acceptor_.accept(socket);
            std::cout << "Socket Accepted" << std::endl;

            std::thread{[q{std::move(socket)}, &prev_data, &market_depth_snapshot_json_data]() {
                boost::beast::websocket::stream<tcp::socket> ws{std::move(const_cast<tcp::socket &>(q))};
                ws.accept();

                // Send the initial data to the client
                if (market_depth_snapshot_json_data.IsNull()) {
                    http::request<http::string_body> req{http::verb::get, "/market_data/get-all-market_depth/", 11};
                    req.set(http::field::host, "127.0.0.1");
                    req.set(http::field::user_agent, BOOST_BEAST_VERSION_STRING);

                    net::io_context ioc;
                    tcp::resolver resolver{ioc};
                    auto const results = resolver.resolve("127.0.0.1", "8040");
                    beast::tcp_stream stream{ioc};
                    stream.connect(results);
                    //send the get-all-market_depth request to server
                    http::write(stream, req);

                    // Read the HTTP response
                    beast::flat_buffer buffer;
                    http::response<http::string_body> res;
                    http::read(stream, buffer, res);

                    market_depth_snapshot_json_data.Parse(res.body().c_str());

                    ws.write(boost::asio::buffer(res.body()));
                } else {
                    // Send the latest data to the client
                    rapidjson::StringBuffer buffer;
                    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
                    //re-use previously extracted data - this should be done only when we are unable to connect to webserver
                    market_depth_snapshot_json_data.Accept(writer);
                    ws.write(boost::asio::buffer(buffer.GetString(), buffer.GetSize()));
                }

                while (true) {
                    http::request<http::string_body> req{http::verb::get, "/market_data/get-all-market_depth/", 11};
                    req.set(http::field::host, "127.0.0.1");
                    req.set(http::field::user_agent, BOOST_BEAST_VERSION_STRING);

                    net::io_context ioc;
                    tcp::resolver resolver{ioc};
                    auto const results = resolver.resolve("127.0.0.1", "8040");
                    beast::tcp_stream stream{ioc};
                    stream.connect(results);
                    http::write(stream, req);

                    // Read the HTTP response
                    beast::flat_buffer buffer;
                    http::response<http::string_body> res;
                    http::read(stream, buffer, res);

                    rapidjson::Document new_data;
                    new_data.Parse(res.body().c_str());

                    if (prev_data.IsNull() || !new_data.IsObject() || !prev_data.IsObject() || prev_data != new_data) {
                        // Update the latest data and send it to the client
                        market_depth_snapshot_json_data.CopyFrom(new_data, market_depth_snapshot_json_data.GetAllocator());

                        rapidjson::StringBuffer buffer;
                        rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
                        market_depth_snapshot_json_data.Accept(writer);
                        ws.write(boost::asio::buffer(buffer.GetString(), buffer.GetSize()));

                        // Update the previous data
                        prev_data.CopyFrom(new_data, prev_data.GetAllocator());
                    }

                    // Wait for 1 second before sending the next update
                    std::this_thread::sleep_for(std::chrono::seconds(1));
                }
            }}.detach();
        }
    }


private:
    net::ip::address address_;
    unsigned short port_;
    net::io_context ioc_;
    tcp::acceptor acceptor_;

};

