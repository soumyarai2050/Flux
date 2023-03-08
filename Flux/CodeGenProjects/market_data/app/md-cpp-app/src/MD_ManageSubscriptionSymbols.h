# pragma once
#include <string>
#include <iostream>
#include <boost/json/src.hpp>
#include <boost/asio.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <utility>


namespace beast = boost::beast;
namespace http = beast::http;
using tcp = boost::asio::ip::tcp;

namespace md_handler {

    struct Symbols{
        std::vector<std::string> symbols;
    };
// This helper function deduces the type and assigns the value with the matching key
    template<class T>
    void extract( boost::json::object const& obj, T& t, std::string_view key )
    {
        t = boost::json::value_to<T>( obj.at( key ) );
    }

    Symbols tag_invoke( boost::json::value_to_tag< Symbols >, boost::json::value const& jv )
    {
        Symbols c;
        boost::json::array const& arr = jv.as_array();
        boost::json::object const& obj = jv.as_object();
        //extract( obj, c.symbols, "symbols" );
        return c;
    }

} // namespace md_handler

class MD_ManageSubscriptionSymbols {
public:

    MD_ManageSubscriptionSymbols(std::string  host, std::string  port, std::string  target) :
    host_(std::move(host)), port_(std::move(port)), target_(std::move(target)) {}

    auto get() {
        static const std::vector<std::string> empty_vector;
        boost::asio::io_context io_context;
        tcp::resolver resolver(io_context);
        beast::tcp_stream stream(io_context);

        auto const endpoints = resolver.resolve(host_, port_);

        stream.connect(endpoints);

        http::request<http::string_body> req{http::verb::get, target_, 11};
        const std::string host_port = host_ + ':' + port_;
        req.set(http::field::host, host_port);

        http::write(stream, req);

        beast::flat_buffer buffer;
        http::response<http::dynamic_body> res;

        http::read(stream, buffer, res);
        std::string response_body;
        // https://www.boost.org/doc/libs/1_81_0/libs/json/doc/html/json/quick_look.html [boost json parsing]
        if (res.result() == boost::beast::http::status::ok){
            response_body = boost::beast::buffers_to_string(res.body().data());
            boost::json::value jv = boost::json::parse( response_body );
            boost::json::array const& arr = jv.as_array();
            boost::json::object const& obj = arr[0].as_object();
            auto vc = value_to< std::vector< std::string > >( obj.at( "symbols" ) );
//            boost::json::array const& arr1 = obj.at( "symbols" ).as_array();
//            for (auto &val: arr1)
//                std::cout << val << std::endl;
            return vc;
        }
        else{
            std::cerr << "symbol request failed for host: " << host_port << std::endl;
            return empty_vector;
        }
    }

private:
    std::string host_;
    std::string port_;
    std::string target_;
};

