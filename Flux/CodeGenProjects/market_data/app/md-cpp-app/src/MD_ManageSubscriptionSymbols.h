# pragma once
#include <string>
#include <iostream>

#include <boost/asio.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>


namespace beast = boost::beast;
namespace http = beast::http;
using tcp = boost::asio::ip::tcp;

class MD_ManageSubscriptionSymbols {
public:

    MD_ManageSubscriptionSymbols(std::string& host, std::string& port, std::string& target) :
    host_(host), port_(port), target_(target) {}

    std::string get() {
        boost::asio::io_context io_context;
        tcp::resolver resolver(io_context);
        beast::tcp_stream stream(io_context);

        auto const results = resolver.resolve(host_, port_);

        stream.connect(results);

        http::request<http::string_body> req{http::verb::get, target_, 11};
        req.set(http::field::host, host_ + ':' + port_);

        http::write(stream, req);

        beast::flat_buffer buffer;
        http::response<http::dynamic_body> res;

        http::read(stream, buffer, res);

        std::string response_body = boost::beast::buffers_to_string(res.body().data());


        return response_body;
    }

private:
    std::string host_;
    std::string port_;
    std::string target_;
};

