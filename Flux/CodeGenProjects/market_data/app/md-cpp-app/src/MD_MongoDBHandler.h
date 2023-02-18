#pragma once
#include <iostream>
#include <sstream>
#include <unordered_map>

#include <bsoncxx/v_noabi/bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/json.hpp>
#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>
#include <Poco/Net/HTTPClientSession.h>
#include <Poco/Net/HTTPRequest.h>
#include <Poco/Net/HTTPResponse.h>
#include <Poco/StreamCopier.h>
#include "MD_TopOfBookPublisher.h"
#include "MD_MarketDepth.h"

namespace md_handler {
    using bsoncxx::builder::basic::make_array;
    using bsoncxx::builder::basic::make_document;
    using bsoncxx::builder::basic::kvp;


// TODO IMPORTANT get URI, DB-Name and Table-Name from config (quick get-env for now ?)
    const std::string db_uri = "mongodb://localhost:27017";
    const std::string market_data_db_name = "market_data";
    const std::string market_data_history = "RawMarketDepthHistory";
    const std::string market_depth = "MarketDepth";
    const std::string top_of_book = "TopOfBook";
    const std::string last_trade = "LastTrade";

//key constants used across classes via constants for consistency
    const std::string symbol_key = "symbol";
    const std::string position_key = "position";
    const std::string side_key = "side";
    const std::string qty_key = "qty";
    const std::string exchange_key = "exchange";
    const std::string px_key = "px";
    const std::string operation_key = "operation";
    const std::string time_key = "time";
    const std::string id_key = "_id";

    inline auto get_symbol_side_query(const std::string &symbol, const std::string &side){
        auto query = bsoncxx::builder::stream::document{}
                << "symbol" << symbol << "side" << side
                << bsoncxx::builder::stream::finalize;
        return query;
    }



    class MD_MongoDBHandler {
    public:
        // The mongocxx::instance constructor & destructor initialize / shut-down the driver, thus mongocxx::instance must
        // be created before using the driver must remain alive for as long as the driver is in use
        mongocxx::instance inst{};
        mongocxx::client conn{mongocxx::uri{db_uri}};
        mongocxx::database market_data_db = conn[market_data_db_name];
    };


}