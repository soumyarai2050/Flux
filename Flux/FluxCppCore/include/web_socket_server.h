# pragma once

#include <string>
#include <thread>
#include <vector>
#include <chrono>

#include <boost/beast/http.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/asio.hpp>

#include "utility_functions.h"
#include "project_includes.h"
#include "mongo_db_codec.h"

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
        explicit WebSocketServer(UserDataType &user_data, MongoDBCodec<RootModelType, RootModelListType>& mongo_db_codec,
            const int32_t db_limit, const std::string& kr_host = market_data_handler::host,
            const int32_t k_web_socket_server_port = stoi(market_data_handler::port),
            const std::chrono::seconds k_read_timeout = std::chrono::seconds(market_data_handler::connection_timeout)) :
        m_user_data(user_data), m_mongo_db_codec_(mongo_db_codec), m_db_fetch_limit_(db_limit),
        km_host_(kr_host), km_port_(k_web_socket_server_port),
        km_read_timeout_seconds_(std::chrono::duration_cast<std::chrono::seconds>(k_read_timeout).count()),
        m_timer_(m_io_context_, km_read_timeout_seconds_) {
            start_connection();
            m_ws_run_thread_ = std::jthread([this]() {
                run();
            });
        }

        [[nodiscard]] bool has_ws_clients_connected() const {
            return not ws_vector_.empty();
        }

        virtual ~WebSocketServer(){
            ws_vector_.clear();
        }

        void clean_ws() {
            m_shutdown_ = true;
            m_io_context_.stop();
        }

        bool publish(const std::string &kr_send_string, const int32_t k_new_client_ws_id  = -1)
        {
            boost::system::error_code error_code;

            if(-1 == k_new_client_ws_id){
                for(auto &ws_ptr: ws_vector_){
                    ws_ptr->write(asio::buffer(kr_send_string), error_code);
                }
            } else{
                ws_vector_[k_new_client_ws_id]->write(asio::buffer(kr_send_string), error_code);
            }

            if (!error_code) {
                return true;
            } else {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error writing data to client: {};;; Data {}", error_code.message(), kr_send_string);
                return false;
            }
        }

        bool publish(const RootModelType &kr_root_model_type_obj, const int16_t k_new_client_ws_id  = -1) {
            boost::json::object json_object;
            MarketDataObjectToJson::object_to_json(kr_root_model_type_obj, json_object);
            if (has_ws_clients_connected()) {
                publish(boost::json::serialize(json_object), k_new_client_ws_id);
            }
            return true;
        }

        bool publish(const RootModelListType &kr_root_model_list_type_obj, const int16_t k_new_client_ws_id  = -1) {
            boost::json::object json_object;
            std::string key;
            MarketDataObjectToJson::object_to_json(kr_root_model_list_type_obj, json_object);
            if (has_ws_clients_connected()) {
                for (const auto &obj : json_object) {
                    key = std::string(obj.key());
                }
                publish(boost::json::serialize(json_object[key].as_array()), k_new_client_ws_id);
            }
            return true;
        }

        void shutdown(){
            m_shutdown_ = true;
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
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Error while accepting client: {}", error.what());
                }
                // Send the HTTP response body to the WebSocket client
                ws_vector_.push_back(std::move(ws_ptr));
                RootModelListType list_user_data;
                m_mongo_db_codec_.get_data_from_collection_with_limit(list_user_data, m_db_fetch_limit_);
                publish(list_user_data, ws_vector_.size()-1);
                // invoke callback to let user know of this new client with index
            }
            catch (std::exception const& error) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Session error: {}", error.what());
            }
        }

        void start_connection() {
            try {
                m_acceptor_ = std::make_unique<tcp::acceptor>(m_io_context_,
                    tcp::endpoint{asio::ip::make_address(km_host_), static_cast<port_type>(km_port_)});
            } catch (const boost::system::system_error& error) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Failed to start server: {} in function: {}", error.what(), __func__);
                std::string kill_command = "kill -9 $(lsof -t -i :" + std::to_string(km_port_) + ")";
                system(kill_command.c_str());
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
                m_timer_.expires_from_now(km_read_timeout_seconds_); // reset the timer
                run();
            });

            m_timer_.async_wait([&](const boost::system::error_code &error_code) {
                if (!error_code) {
                    shutdown();
                    if(m_shutdown_)
                        m_io_context_.stop();
                    else
                        m_io_context_.run();

                }
            });

            m_io_context_.run();
        }

        UserDataType& m_user_data;
        MongoDBCodec<RootModelType, RootModelListType>& m_mongo_db_codec_;
        int32_t m_db_fetch_limit_;
        std::string km_host_;
        int32_t km_port_;
        int32_t m_ws_retry_count_{3};
        const boost::posix_time::seconds km_read_timeout_seconds_;
        std::string json_str_;
        std::vector<std::shared_ptr<websocket::stream<tcp::socket>>> ws_vector_;
        std::vector <std::thread> m_ws_client_threads_;
        bool m_shutdown_ = false;
        asio::io_context m_io_context_;
        // interval to timeout read if no data and handle any shutdown if requested
        boost::asio::deadline_timer m_timer_;
        std::unique_ptr<tcp::acceptor> m_acceptor_;
        std::jthread m_ws_run_thread_;
    };

}
