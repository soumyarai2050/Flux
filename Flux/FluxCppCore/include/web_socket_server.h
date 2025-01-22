# pragma once

#include <string>
#include <thread>
#include <vector>
#include <chrono>

#include <boost/beast/http.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/asio.hpp>

#include "utility_functions.h"
#include "web_socket_route_handler.h"

namespace beast = boost::beast;
namespace http = beast::http;
namespace websocket = beast::websocket;
namespace asio = boost::asio;

using boost::asio::ip::tcp;
using boost::asio::ip::address;
using boost::asio::ip::port_type;

namespace FluxCppCore {

    class WebSocketServer {
    public:
        // Structure to hold WebSocket connections for a specific route
        struct RouteConnections {
            std::vector<std::shared_ptr<websocket::stream<tcp::socket>>> connections;
            std::shared_ptr<WebSocketRouteHandler> handler;

            void publish(const std::string& message) {
                boost::system::error_code error_code;
                for (auto it = connections.begin(); it != connections.end();) {
                    auto& ws_ptr = *it;
                    ws_ptr->write(asio::buffer(message), error_code);
                    if (error_code) {
                        std::cout << std::format( "WebSocketServer: Error writing data to client. Error: {};;; Data: {}",
                                     error_code.message(), message);
                        LOG_ERROR_IMPL(GetCppAppLogger(), "WebSocketServer: Error writing data to client. Error: {};;; Data: {}",
                                     error_code.message(), message);
                        it = connections.erase(it);
                    } else {
                        ++it;
                    }
                }
            }
        };

        explicit WebSocketServer(const std::string& host, int32_t port, std::chrono::seconds read_timeout)
            : km_host_(host), km_port_(port),
              km_read_timeout_seconds_(std::chrono::duration_cast<std::chrono::seconds>(read_timeout).count()),
              m_timer_(m_io_context_, km_read_timeout_seconds_) {

            if (start_connection()) {
                m_ws_run_thread_ = std::jthread([this]() {
                    run();
                });
                LOG_INFO_IMPL(GetCppAppLogger(), "WebSocketServer: Started WebSocket server on {}:{}", km_host_, km_port_);
            } else {
                LOG_ERROR_IMPL(GetCppAppLogger(), "WebSocketServer: Failed to start WebSocket server on {}:{}", km_host_, km_port_);
            }
        }

        // Register a route handler
        void register_route_handler(std::shared_ptr<WebSocketRouteHandler> handler) {
            auto route_path = handler->get_route_path();
            m_routes_[route_path] = std::make_shared<RouteConnections>();
            m_routes_[route_path]->handler = handler;
            m_routes_.size();
        }

        bool publish_to_route(const std::string& route, const std::string& message) {
            auto route_it = m_routes_.find(route);
            if (route_it == m_routes_.end()) {
                std::cout << std::format( "WebSocketServer: Invalid route: {}", route) << std::endl;
                LOG_ERROR_IMPL(GetCppAppLogger(), "WebSocketServer: Invalid route: {}", route);
                return false;
            }
            route_it->second->publish(message);
            return true;
        }

        [[nodiscard]] bool has_ws_clients_connected() const {
            for (const auto& [route, connections] : m_routes_) {
                if (!connections->connections.empty()) {
                    return true;
                }
            }
            return false;
        }

        virtual ~WebSocketServer() {
            for (auto& [route, connections] : m_routes_) {
                connections->connections.clear();
            }
            m_routes_.clear();
        }

        void clean_ws() {
            m_shutdown_ = true;
            m_io_context_.stop();
        }

        void shutdown() {
            m_shutdown_ = true;
        }

    protected:
        void session(tcp::socket socket) {
            try {
                beast::flat_buffer buffer;
                http::request<http::string_body> req;
                http::read(socket, buffer, req);

                std::string path = std::string(req.target());
                std::cout << "Client requested path: " << path << std::endl;

                auto route_it = m_routes_.find(path);
                if (route_it == m_routes_.end()) {
                    LOG_ERROR_IMPL(GetCppAppLogger(), "WebSocketServer: Unsupported route: {}", path);
                    return;
                }

                auto ws_ptr = std::make_shared<websocket::stream<tcp::socket>>(std::move(socket));
                try {
                    ws_ptr->accept(req);
                    route_it->second->connections.push_back(ws_ptr);

                    // Call the route handler for the new connection
                    if (route_it->second->handler) {
                        route_it->second->handler->handle_new_connection(ws_ptr);
                    }
                }
                catch (std::exception const& error) {
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Error while accepting client: {}", error.what());
                }
            }
            catch (std::exception const& error) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "WebSocketServer: Session error occurred. Host: {}, Port: {}. Error: {}",
                              km_host_, km_port_, error.what());
            }
        }

        bool start_connection() {
            try {
                m_acceptor_ = std::make_unique<tcp::acceptor>(m_io_context_,
                    tcp::endpoint{asio::ip::make_address(km_host_), static_cast<asio::ip::port_type>(km_port_)});
                return true;
            } catch (const boost::system::system_error& error) {
                std::string err_msg = error.what();
                if (error.code().value() == 98 || err_msg.contains("bind: Address already in use")) {
                    --m_ws_retry_count_;
                    if (m_ws_retry_count_ > 0) {
                        usleep(0.5);
                        return start_connection();
                    } else {
                        LOG_ERROR_IMPL(GetCppAppLogger(), "WebSocketServer: Failed to start server on Host: {}, Port: {}. "
                                                  "Error: {}. Retrying...", km_host_, km_port_, error.what());
                        return false;
                    }
                } else {
                    LOG_ERROR_IMPL(GetCppAppLogger(), "WebSocketServer: Failed to start server on Host: {}, Port: {}. "
                                                  "Error: {}. Retrying...", km_host_, km_port_, error.what());
                    return false;
                }
            }
        }

        void run() {
            auto sp_socket = std::make_shared<tcp::socket>(m_io_context_);
            m_acceptor_->async_accept(*sp_socket, [&](const boost::system::error_code& error_code) {
                m_timer_.cancel(); // cancel the timer when a connection is accepted
                if (!error_code) {
                    session(std::move(*sp_socket));
                    // Create a new sp_socket object to be used for the next connection (old socket is moved thus sp_socket obj is free for reuse)
                    sp_socket = std::make_shared<tcp::socket>(m_io_context_);
                }
                m_timer_.expires_from_now(km_read_timeout_seconds_); // reset the timer
                run();
            });

            m_timer_.async_wait([&](const boost::system::error_code& error_code) {
                if (!error_code) {
                    shutdown();
                    if (m_shutdown_)
                        m_io_context_.stop();
                    else
                        m_io_context_.run();
                }
            });

            m_io_context_.run();
        }

    private:
        std::string km_host_;
        int32_t km_port_;
        const boost::posix_time::seconds km_read_timeout_seconds_;
        std::unordered_map<std::string, std::shared_ptr<RouteConnections>> m_routes_;
        bool m_shutdown_ = false;
        asio::io_context m_io_context_;
        boost::asio::deadline_timer m_timer_;
        std::unique_ptr<tcp::acceptor> m_acceptor_;
        std::jthread m_ws_run_thread_;
        int8_t m_ws_retry_count_{3};
    };


}
