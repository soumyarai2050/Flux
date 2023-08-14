#include "base_web_client.h"

boost::asio::io_context FluxCppCore::BaseWebClient::io_context_;
boost::asio::ip::tcp::resolver FluxCppCore::BaseWebClient::resolver_(io_context_);
boost::asio::ip::tcp::socket FluxCppCore::BaseWebClient::socket_(io_context_);
boost::asio::ip::tcp::resolver::results_type FluxCppCore::BaseWebClient::result_;
