#pragma once

#include <memory>

#include "project_includes.h"
#include "mongo_db_codec.h"
#include "market_data_constants.h"

namespace beast = boost::beast;
namespace http = beast::http;
namespace websocket = beast::websocket;
namespace asio = boost::asio;
using tcp = boost::asio::ip::tcp;


namespace FluxCppCore {

    class WebSocketRouteHandler {
    public:
        virtual ~WebSocketRouteHandler() = default;
        virtual void handle_new_connection(std::shared_ptr<websocket::stream<tcp::socket>> ws_ptr) = 0;
        [[nodiscard]] virtual std::string get_route_path() const = 0;
    };

    class MarketDepthRouteHandler : public WebSocketRouteHandler {
    public:
        explicit MarketDepthRouteHandler(const std::string& r_route_pth,
            FluxCppCore::MongoDBCodec<MarketDepth, MarketDepthList>& db_codec)
            : m_route_path_(r_route_pth), m_db_codec_(db_codec) {}

        void handle_new_connection(std::shared_ptr<websocket::stream<tcp::socket>> ws_ptr) override {
            try {
                MarketDepthList data_list;
                m_db_codec_.get_data_from_collection_with_limit(data_list, market_data_handler::market_depth_limit);

                boost::json::object json_data;
                // Convert your data list to JSON using your existing conversion logic
                if (MarketDataObjectToJson::object_to_json(data_list, json_data)) {
                    boost::system::error_code error_code;
                    ws_ptr->write(asio::buffer(boost::json::serialize(json_data["market_depth"].get_array())), error_code);
                    if (error_code) {
                        LOG_ERROR_IMPL(GetCppAppLogger(), "Error sending initial data: {};;; error: {}",
                            boost::json::serialize(json_data["market_depth"].get_array()), error_code.message());
                    }
                } else {
                    std::ostringstream os;
                    for (const auto& item : data_list.market_depth_) {
                        os << "id: " << item.id_ << " symbol: " << item.symbol_ << "\n";
                    }
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Error while serailizing market depth: {}", os.str());
                }
            } catch (const std::exception& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error fetching initial data of market depth: {}", e.what());
            }
        }

        [[nodiscard]] std::string get_route_path() const override {
            return m_route_path_;
        }

    private:
        const std::string& m_route_path_;
        FluxCppCore::MongoDBCodec<MarketDepth, MarketDepthList>& m_db_codec_;
    };


    class LastTradeRouteHandler : public WebSocketRouteHandler {
    public:
        explicit LastTradeRouteHandler(const std::string& r_route_pth,
            FluxCppCore::MongoDBCodec<LastTrade, LastTradeList>& db_codec)
            : m_route_path_(r_route_pth), m_db_codec_(db_codec) {}

        void handle_new_connection(std::shared_ptr<websocket::stream<tcp::socket>> ws_ptr) override {
            try {
                LastTradeList data_list;
                m_db_codec_.get_data_from_collection_with_limit(data_list, market_data_handler::last_trade_limit);

                boost::json::object json_data;
                // Convert your data list to JSON using your existing conversion logic
                if (MarketDataObjectToJson::object_to_json(data_list, json_data)) {
                    boost::system::error_code error_code;
                    ws_ptr->write(asio::buffer(boost::json::serialize(json_data["last_trade"].get_array())), error_code);
                    if (error_code) {
                        LOG_ERROR_IMPL(GetCppAppLogger(), "Error sending initial data: {};;; error: {}",
                            boost::json::serialize(json_data["last_trade"].get_array()), error_code.message());
                    }
                } else {
                    std::ostringstream os;
                    for (const auto& item : data_list.last_trade_) {
                        os << "id: " << item.id_ << " symbol: " << item.symbol_n_exch_id_.symbol_ << "\n";
                    }
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Error while serailizing last trade: {}", os.str());
                }
            } catch (const std::exception& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error fetching initial data of last trade: {}", e.what());
            }
        }

        [[nodiscard]] std::string get_route_path() const override {
            return m_route_path_;
        }

    private:
        const std::string& m_route_path_;
        FluxCppCore::MongoDBCodec<LastTrade, LastTradeList>& m_db_codec_;
    };


    class TopOfBookRouteHandler : public WebSocketRouteHandler {
    public:
        explicit TopOfBookRouteHandler(const std::string& r_route_pth,
            FluxCppCore::MongoDBCodec<TopOfBook, TopOfBookList>& db_codec)
            : m_route_path_(r_route_pth), m_db_codec_(db_codec) {}

        void handle_new_connection(std::shared_ptr<websocket::stream<tcp::socket>> ws_ptr) override {
            try {
                TopOfBookList data_list;
                m_db_codec_.get_data_from_collection_with_limit(data_list, market_data_handler::top_of_book_limit);

                boost::json::object json_data;
                // Convert your data list to JSON using your existing conversion logic
                if (MarketDataObjectToJson::object_to_json(data_list, json_data)) {
                    boost::system::error_code error_code;
                    ws_ptr->write(asio::buffer(boost::json::serialize(json_data["top_of_book"].get_array())), error_code);
                    if (error_code) {
                        LOG_ERROR_IMPL(GetCppAppLogger(), "Error sending initial data: {};;; error: {}",
                            boost::json::serialize(json_data["top_of_book"].get_array()), error_code.message());
                    }
                } else {
                    std::ostringstream os;
                    for (const auto& item : data_list.top_of_book_) {
                        os << "id: " << item.id_ << " symbol: " << item.symbol_ << "\n";
                    }
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Error while serailizing top of book: {}", os.str());
                }
            } catch (const std::exception& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error fetching initial data of top of book: {}", e.what());
            }
        }

        [[nodiscard]] std::string get_route_path() const override {
            return m_route_path_;
        }

    private:
        const std::string& m_route_path_;
        FluxCppCore::MongoDBCodec<TopOfBook, TopOfBookList>& m_db_codec_;
    };

}