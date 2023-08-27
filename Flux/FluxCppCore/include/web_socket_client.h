//
// Created by pc on 8/16/2023.
//

#pragma once

#include <iostream>
#include <string>

#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/json/src.hpp>
#include <boost/asio.hpp>
#include <boost/asio/deadline_timer.hpp>

#include "json_codec.h"
#include "../../../../CodeGenProjects/market_data/generated/ProtoGenCc/market_data_service.pb.h"

namespace beast = boost::beast;
namespace http = beast::http;
namespace websocket = beast::websocket;
namespace net = boost::asio;
using tcp = boost::asio::ip::tcp;

template <typename UserDataType>
class WebSocketClient {
public:
    explicit WebSocketClient(UserDataType &user_data, const std::string k_server_address = "127.0.0.1",
                             const int32_t port = 8083,
                             quill::Logger *p_logger = quill::get_logger()) :
                             km_user_data_type_name_(UserDataType::GetDescriptor()->name()),
                             m_server_address_(k_server_address), m_port_(port), m_resolver_(m_io_context_),
                             m_ws_(m_io_context_), m_user_data_(user_data), mp_logger_(p_logger) {}

    void run() {
        auto const results = m_resolver_.resolve(m_server_address_, std::to_string(m_port_));
        net::connect(m_ws_.next_layer(), results.begin(), results.end());

        m_ws_.handshake(m_server_address_, "/");

        m_update_received_ = false;

        // Start an asynchronous read operation to continuously read data from the WebSocket
        read_data_from_server();

        // Run the Boost.Asio event loop until the client is stopped
        m_io_context_.run();
    }

    void shutdown() {
        m_io_context_.stop();
    }

    void get_received_data(UserDataType &user_data) {
        user_data = m_user_data_;
    }

private:
    void read_data_from_server() {
        m_deadline_timer_.expires_from_now(boost::posix_time::seconds(10)); // Set the timeout to 10 seconds
        m_ws_.async_read(m_buffer_, [this](boost::system::error_code error_code, std::size_t bytes_transferred) {
            m_deadline_timer_.cancel();
            bool status = false;
            if (!error_code) {
                m_update_received_ = true;
                std::string data;
                data = (beast::buffers_to_string(m_buffer_.data()));
                m_buffer_.consume(m_buffer_.size());
                const std::string target = "List";
                if (km_user_data_type_name_.find(target) == std::string::npos) {
                    status = FluxCppCore::RootModelJsonCodec<UserDataType>::decode_model(m_user_data_, data);
                } else {
                    status = FluxCppCore::RootModelListJsonCodec<UserDataType>::decode_model_list(m_user_data_, data);
                }
                if (status) {
                    LOG_INFO(mp_logger_, "Received data: {}", data);
                    LOG_INFO(mp_logger_, "Deserialized data: {} ", m_user_data_.DebugString());
                } else {
                    LOG_ERROR(mp_logger_, "Failed while decoding received Data: {};;; UserDataType: {} ",
                              data, km_user_data_type_name_);
                }

                // Continue reading data by initiating the next read operation
                read_data_from_server();
            } else if (error_code == boost::asio::error::operation_aborted) {
                // Reading operation was canceled, exit the loop
                shutdown();
            } else if (error_code == websocket::error::closed || error_code == boost::asio::error::connection_reset) {
                // WebSocket closed or connection reset by peer, exit the loop
                shutdown();
            } else {
                LOG_ERROR(mp_logger_, "Error reading from WebSocket: {}", error_code.message());
            }
        });

        // Set up a callback for the deadline timer
        m_deadline_timer_.async_wait([this](boost::system::error_code ec) {
            if (!ec) {
                // No update received for the specified time, stop the client
                shutdown();
            }
        });
    }

    const std::string km_user_data_type_name_;
    std::string m_server_address_;
    int32_t m_port_;
    net::io_context m_io_context_;
    tcp::resolver m_resolver_;
    net::deadline_timer m_deadline_timer_{m_io_context_};
    bool m_update_received_{false};
    websocket::stream<tcp::socket> m_ws_;
    beast::flat_buffer m_buffer_;
    UserDataType m_user_data_;
    quill::Logger *mp_logger_;
};

