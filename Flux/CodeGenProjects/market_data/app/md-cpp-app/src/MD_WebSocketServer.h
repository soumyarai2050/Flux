//
// Created by pc on 2/27/2023.
//

#ifndef MD_HANDLER_MD_WEBSOCKETSERVER_H
#define MD_HANDLER_MD_WEBSOCKETSERVER_H

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


    void run()
    {
        while (true) {
            tcp::socket socket{ioc_};
            acceptor_.accept(socket);
            std::cout << "Socket Accepted" << std::endl;

            std::thread{[q {std::move(socket)}]() {
                boost::beast::websocket::stream<tcp::socket> ws {std::move(const_cast<tcp::socket&>(q))};
                ws.accept();

                std::string latest_data;

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

                    ws.write(boost::asio::buffer(res.body()));


                    // Parse the JSON data
                    rapidjson::Document doc;
                    doc.Parse(res.body().c_str());

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

#endif //MD_HANDLER_MD_WEBSOCKETSERVER_H
