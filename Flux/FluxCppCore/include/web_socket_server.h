# pragma once

#include <string>
#include <thread>
#include <vector>
#include <chrono>

#include <boost/beast/http.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/asio.hpp>
#include "quill/Quill.h"

#include "json_codec.h"
#include "utility_functions.h"
// #include "cpp_app_shared_resource.h"
#include "../../CodeGenProjects/TradeEngine/ProjectGroup/market_data/cpp_app/replay/cpp_app_shared_resource.h"
#include "../../CodeGenProjects/TradeEngine/ProjectGroup/market_data/generated/CppUtilGen/market_data_constants.h"

namespace beast = boost::beast;
namespace http = beast::http;
namespace websocket = beast::websocket;
namespace asio = boost::asio;

using boost::asio::ip::tcp;
using boost::asio::ip::address;
using boost::asio::ip::port_type;

namespace FluxCppCore {
    template <typename RootModelType, typename RootModelListType, typename UserDataType>
    class WebSocketServer {
    public:
        explicit WebSocketServer(UserDataType &user_data, const std::string k_host = market_data_handler::host,
                                 const int32_t k_web_socket_server_port = stoi(market_data_handler::port),
                                 const std::chrono::seconds k_read_timeout =
                                 std::chrono::seconds(market_data_handler::connection_timeout),
                                 quill::Logger *p_logger = GetLogger()) :
        m_user_data(user_data), km_host_(k_host), km_port_(k_web_socket_server_port),
        km_read_timeout_seconds(std::chrono::duration_cast<std::chrono::seconds>(k_read_timeout).count()),
        m_timer_(m_io_context_, km_read_timeout_seconds), mp_logger(p_logger) {
            start_connection();
        }

        void start_connection() {
            try {
                m_acceptor_ = std::make_unique<tcp::acceptor>(m_io_context_,
                    tcp::endpoint{asio::ip::make_address(km_host_), static_cast<port_type>(km_port_)});
            } catch (const boost::system::system_error& error) {
                LOG_ERROR_IMPL(mp_logger, "Failed to start server: {} in function: {}", error.what(), __func__);
                LOG_INFO_IMPL(mp_logger, "Retrying server initialization in function: {}", __func__);
                start_connection();
            }
        }

        void run() {
            std::shared_ptr sp_socket = std::make_shared<tcp::socket>(m_io_context_);
            m_acceptor_->async_accept(*sp_socket, [&](const boost::system::error_code &error_code) {
                m_timer_.cancel(); // cancel the timer when a connection is accepted
                if (!error_code) {
                    session(std::move(*sp_socket));
                    // Create a new sp_socket object to be used for the next connection (old socked is moved thus sp_socket obj is free for reuse)
                    sp_socket = std::make_shared<tcp::socket>(m_io_context_);
                }
                m_timer_.expires_from_now(km_read_timeout_seconds); // reset the timer
                run();
            });

            m_timer_.async_wait([&](const boost::system::error_code &error_code) {
                if (!error_code) {
                    shutdown();
                    LOG_INFO_IMPL(mp_logger, "Timeout reached");
                    if(m_shutdown)
                        m_io_context_.stop();
                    else
                        m_io_context_.run();

                }
            });

            m_io_context_.run();
        }

        bool has_ws_clients_connected(){
            return not ws_vector.empty();
        }

        ~WebSocketServer(){
            m_shutdown = true;
            ws_vector.clear();
        }

        bool publish(const std::string &kr_send_string, const int32_t k_new_client_ws_id  = -1)
        {
            boost::system::error_code error_code;
            std::string string_to_send = kr_send_string;

            std::size_t found = string_to_send.find("id");
            if (found != std::string::npos) {
                // Replace "id" with "_id"
                string_to_send.replace(found, 2, "_id");
            }

            if(-1 == k_new_client_ws_id){
                for(auto &ws_ptr: ws_vector){
                    ws_ptr->write(asio::buffer(string_to_send), error_code);
                }
            } else{
                ws_vector[k_new_client_ws_id]->write(asio::buffer(string_to_send), error_code);
            }

            if (!error_code) {
                return true;
            } else {
                LOG_ERROR_IMPL(mp_logger, "Error writing data to client: {};;; Data {}", error_code.message(), kr_send_string);
                return false;
            }
        }

        bool publish(const RootModelType &kr_root_model_type_obj, const int16_t k_new_client_ws_id  = -1) {
            std::string json;
            bool status = FluxCppCore::RootModelJsonCodec<RootModelType>::encode_model(kr_root_model_type_obj, json);
            if (has_ws_clients_connected() and status) {
                status = publish(json, k_new_client_ws_id);
            }
            return status;
        }

        bool publish(const RootModelListType &kr_root_model_list_type_obj, const int16_t k_new_client_ws_id  = -1) {
            std::string json;
            bool status = FluxCppCore::RootModelListJsonCodec<RootModelListType>::encode_model_list
                    (kr_root_model_list_type_obj, json);
            if (has_ws_clients_connected() and status) {
                status = publish(json, k_new_client_ws_id);
            }

            return status;
        }

        void shutdown(){
            m_shutdown = true;
        }

        virtual bool NewClientCallBack(UserDataType &user_data, int16_t new_client_web_socket_id) = 0;

    protected:

        void session(tcp::socket socket) {
            try {
                std::shared_ptr<websocket::stream<tcp::socket>> ws_ptr = std::make_shared<websocket::stream<tcp::socket>>(std::move(socket));
                try {
                    ws_ptr->accept();
                }
                catch (std::exception const& error){
                    LOG_ERROR_IMPL(mp_logger, "Error while accepting client: {}", error.what());
                }
                // Send the HTTP response body to the WebSocket client
                ws_vector.push_back(std::move(ws_ptr));
                NewClientCallBack(m_user_data, ws_vector.size()-1);
                // invoke callback to let user know of this new client with index
            }
            catch (std::exception const& error) {
                LOG_ERROR_IMPL(mp_logger, "Session error: {}", error.what());
            }
        }

        UserDataType m_user_data;
        const std::string km_host_;
        int32_t km_port_;
        const boost::posix_time::seconds km_read_timeout_seconds;
        std::string json_str_;
        std::vector<std::shared_ptr<websocket::stream<tcp::socket>>> ws_vector;
        std::vector <std::thread> m_ws_client_threads;
        bool m_shutdown = false;
        asio::io_context m_io_context_;
        // interval to timeout read if no data and handle any shutdown if requested
        boost::asio::deadline_timer m_timer_;
        quill::Logger *mp_logger;
        std::unique_ptr<tcp::acceptor> m_acceptor_;
    };

}
