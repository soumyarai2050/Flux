#include "base_web_client.h"

using namespace FluxCppCore;

boost::asio::io_context BaseWebClient::c_io_context_;
boost::asio::ip::tcp::resolver BaseWebClient::c_resolver_(c_io_context_);
boost::asio::ip::tcp::socket BaseWebClient::c_socket_(c_io_context_);
boost::asio::ip::tcp::resolver::results_type BaseWebClient::c_result_;
std::mutex BaseWebClient::c_market_data_web_client_mutex;
