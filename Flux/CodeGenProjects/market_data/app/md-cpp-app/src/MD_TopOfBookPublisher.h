#pragma once

#include <unordered_map>
#include <sstream>
#include <iostream>
#include <mutex>

#include <Poco/StreamCopier.h>
#include <Poco/Net/HTTPResponse.h>
#include <Poco/Net/HTTPRequest.h>
#include <Poco/Net/HTTPClientSession.h>
#include <mongocxx/instance.hpp>
#include <mongocxx/client.hpp>

#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

#include "MD_Utils.h"
#include "MD_DepthSingleSide.h"
#include "MD_MongoDBHandler.h"
#include "MD_LastTrade.h"

namespace md_handler {
    // TODO From Config
    const std::string host = getenv("HOST") ? getenv("HOST") : "127.0.0.1";
    const int port = 8040;
    const std::string post_uri = "/market_data/create-top_of_book";
    const std::string patch_uri = "/market_data/patch-top_of_book";

    class MD_TopOfBookPublisher {
    protected:
        Poco::Net::HTTPClientSession session;
        Poco::Net::HTTPRequest request;
        Poco::Net::HTTPResponse response;
        static inline md_handler::MD_LastTrade _emptyLastTrade{};
        const static inline md_handler::MD_MktOverview _emptyMktOverview{_emptyLastTrade, 0};
        const static inline md_handler::MD_DepthSingleSide _emptyMarketDepth{};
        static std::unordered_map<std::string, std::string> top_of_book_cache;

    public:
        MD_TopOfBookPublisher() : session(host, port) {
        }

        // Return empty string if ID not found
        static std::string GetDBIdForSymbol(const std::string &symbol){
            const auto itr = top_of_book_cache.find(symbol);
            if (itr != top_of_book_cache.end()){
                return itr->second;
            }
            else{
                return "";
            }
        }

        //Returns false if cache already has the id else adds to cache and returns true
        static bool UpdateTopOfBookCache(const std::string& symbol, const std::string& dbId){
            //TODO make this thread safe if we ever add multi-thread to any of the callers
            const auto itr = top_of_book_cache.find(symbol);
            if (itr == top_of_book_cache.end()){
                top_of_book_cache[symbol] = dbId;
                return true;
            }
            else{
                return false; // id found in cache
            }
        }

        // TODO - not thread safe - make this mutex guarded in case we embark multi threaded
        std::string GetWebResponseFromSession(const std::string &uri, const std::string &symbol = ""){
            return "";
        }

        std::string
        create_data(const md_handler::MD_DepthSingleSide &bid_market_depth,
                    const md_handler::MD_DepthSingleSide &ask_market_depth){
            return create_data(bid_market_depth, ask_market_depth, _emptyMktOverview);
        }

        std::string
        create_data(const md_handler::MD_MktOverview &mkt_overview){
            return create_data(_emptyMarketDepth, _emptyMarketDepth, mkt_overview);
        }

        std::string
        create_data(const md_handler::MD_DepthSingleSide &bid_market_depth,
                    const md_handler::MD_DepthSingleSide &ask_market_depth,
                    const md_handler::MD_MktOverview &mkt_overview){
            const md_handler::MD_LastTrade &lastTrade = mkt_overview.getLastTrade();
            request = Poco::Net::HTTPRequest(Poco::Net::HTTPRequest::HTTP_POST, post_uri);
            request.setContentType("application/json");
            request.add("Accept", "application/json");

            std::string symbol =  bid_market_depth.isEmpty() ? ask_market_depth.getSymbol() : bid_market_depth.getSymbol();
            if (symbol.empty())
                symbol = lastTrade.getSymbol();
            if (symbol.empty()){
                std::cerr << "no symbol sent - dropping create request!" << std::endl;
                return "";
            }
            std::string &&bid_str_date_time = get_date_time_str_from_milliseconds(bid_market_depth.getMillisecondsSinceEpoch());
            std::string &&ask_str_date_time = get_date_time_str_from_milliseconds(ask_market_depth.getMillisecondsSinceEpoch());
            std::string &&last_trade_str_date_time = get_date_time_str_from_milliseconds(lastTrade.getMillisecondsSinceEpoch());
            std::string str_date_time = bid_market_depth.getMillisecondsSinceEpoch() >
                    ask_market_depth.getMillisecondsSinceEpoch()? bid_str_date_time : ask_str_date_time;
            if(lastTrade.getMillisecondsSinceEpoch() != 0 &&
            lastTrade.getMillisecondsSinceEpoch() > bid_market_depth.getMillisecondsSinceEpoch() &&
            lastTrade.getMillisecondsSinceEpoch() > ask_market_depth.getMillisecondsSinceEpoch()){
                str_date_time = last_trade_str_date_time;
            }

            rapidjson::Document create_top_of_book;
            auto &create_top_of_book_alloc = create_top_of_book.GetAllocator();
            create_top_of_book.SetObject();

            rapidjson::Value symbol_textPart;
            symbol_textPart.SetString(symbol.c_str(), create_top_of_book_alloc);
            create_top_of_book.AddMember("symbol", symbol_textPart, create_top_of_book_alloc);

            create_top_of_book.AddMember("total_trading_security_size", mkt_overview.getTotalTradingSecSize(), create_top_of_book_alloc);

            rapidjson::Value bid_quote_object(rapidjson::kObjectType);
            bid_quote_object.AddMember("px", bid_market_depth.getPx(), create_top_of_book_alloc);
            bid_quote_object.AddMember("qty", bid_market_depth.getQty(), create_top_of_book_alloc);
            if (not bid_str_date_time.empty()){
                rapidjson::Value date_time_textPart;
                date_time_textPart.SetString(bid_str_date_time.c_str(), create_top_of_book_alloc);
                bid_quote_object.AddMember("last_update_date_time", date_time_textPart, create_top_of_book_alloc);
            }
            create_top_of_book.AddMember("bid_quote", bid_quote_object, create_top_of_book_alloc);

            rapidjson::Value ask_quote_object(rapidjson::kObjectType);
            ask_quote_object.AddMember("px", ask_market_depth.getPx(), create_top_of_book_alloc);
            ask_quote_object.AddMember("qty", ask_market_depth.getQty(), create_top_of_book_alloc);
            if (not ask_str_date_time.empty()){
                rapidjson::Value date_time_textPart;
                date_time_textPart.SetString(ask_str_date_time.c_str(), create_top_of_book_alloc);
                ask_quote_object.AddMember("last_update_date_time", date_time_textPart, create_top_of_book_alloc);
            }
            create_top_of_book.AddMember("ask_quote", ask_quote_object, create_top_of_book_alloc);

            // last trade we set irrespective
            rapidjson::Value last_trade_object(rapidjson::kObjectType);
            last_trade_object.AddMember("px", lastTrade.getPx(), create_top_of_book_alloc);
            last_trade_object.AddMember("qty", lastTrade.getQty(), create_top_of_book_alloc);
            if (not last_trade_str_date_time.empty()){
                rapidjson::Value date_time_textPart;
                date_time_textPart.SetString(last_trade_str_date_time.c_str(), create_top_of_book_alloc);
                last_trade_object.AddMember("last_update_date_time", date_time_textPart, create_top_of_book_alloc);
            }
            create_top_of_book.AddMember("last_trade", last_trade_object, create_top_of_book_alloc);

            if (not str_date_time.empty()){
                rapidjson::Value date_time_textPart;
                date_time_textPart.SetString(str_date_time.c_str(), create_top_of_book_alloc);
                create_top_of_book.AddMember("last_update_date_time", date_time_textPart, create_top_of_book_alloc);
            }

            // 3. Stringify the DOM
            rapidjson::StringBuffer buffer;
            rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
            create_top_of_book.Accept(writer);
            const std::string& request_json = buffer.GetString();
            request.setContentLength(request_json.length());
            std::ostream &requestStream = session.sendRequest(request);
            requestStream << request_json;

            std::istream& responseStream = session.receiveResponse(response);
            std::stringstream resp_stream;
            Poco::StreamCopier::copyStream(responseStream, resp_stream);

            const std::string &response_str = resp_stream.str();
            // logging.info this:
            std::cout << "create req: " << request_json << std::endl << "create resp: " << response_str << std::endl;

            if(response_str.length() > 10 && response_str[2] == '_' && response_str[3] == 'i' &&
               response_str[4] == 'd' && response_str[6] == ':' && response_str[7] == '"'){
                const auto pos = response_str.find_first_of('"', 8);
                if(std::string::npos != pos){
                    std::string id = response_str.substr(8, pos-8);
                    top_of_book_cache[symbol] = id;
                    return id;
                }
                else{
                    std::cerr << "Web-call failed to uri: " << post_uri << " for symbol: " << symbol << " response:\n" << response_str << std::endl;
                }
            }
            else{
                std::cout << "http request failed for uri:" << post_uri << " response: " << response_str << std::endl;
            }
            return "";
        }

        //return id if successful , empty string if failed - logging done internally
        std::string patch_data(const std::string& top_of_book_db_id, const md_handler::MD_DepthSingleSide &bid_market_depth,
                   const md_handler::MD_DepthSingleSide &ask_market_depth) {
            request = Poco::Net::HTTPRequest(Poco::Net::HTTPRequest::HTTP_PATCH, patch_uri);
            request.setContentType("application/json");
            request.add("Accept", "application/json");

            const std::string &symbol =  bid_market_depth.isEmpty() ? ask_market_depth.getSymbol() : bid_market_depth.getSymbol();
            std::string &&bid_str_date_time = get_date_time_str_from_milliseconds(bid_market_depth.getMillisecondsSinceEpoch());
            std::string &&ask_str_date_time = get_date_time_str_from_milliseconds(ask_market_depth.getMillisecondsSinceEpoch());
            std::string &str_date_time = bid_market_depth.getMillisecondsSinceEpoch() >
                                         ask_market_depth.getMillisecondsSinceEpoch()? bid_str_date_time : ask_str_date_time;

            rapidjson::Document update_top_of_book;
            auto &update_top_of_book_alloc = update_top_of_book.GetAllocator();
            update_top_of_book.SetObject();

            rapidjson::Value id_textPart;
            id_textPart.SetString(top_of_book_db_id.c_str(), update_top_of_book_alloc);
            update_top_of_book.AddMember("_id", id_textPart, update_top_of_book_alloc);
            rapidjson::Value symbol_textPart;
            symbol_textPart.SetString(symbol.c_str(), update_top_of_book_alloc);
            update_top_of_book.AddMember("symbol", symbol_textPart, update_top_of_book_alloc);

            if (not bid_market_depth.isEmpty()) {
                rapidjson::Value bid_quote_object(rapidjson::kObjectType);
                bid_quote_object.AddMember("px", bid_market_depth.getPx(), update_top_of_book_alloc);
                bid_quote_object.AddMember("qty", bid_market_depth.getQty(), update_top_of_book_alloc);
                if (not bid_str_date_time.empty()){
                    rapidjson::Value date_time_textPart;
                    date_time_textPart.SetString(bid_str_date_time.c_str(), update_top_of_book_alloc);
                    bid_quote_object.AddMember("last_update_date_time", date_time_textPart, update_top_of_book_alloc);
                }
                update_top_of_book.AddMember("bid_quote", bid_quote_object, update_top_of_book_alloc);
            }
            else if (not ask_market_depth.isEmpty()) {
                rapidjson::Value ask_quote_object(rapidjson::kObjectType);
                ask_quote_object.AddMember("px", ask_market_depth.getPx(), update_top_of_book_alloc);
                ask_quote_object.AddMember("qty", ask_market_depth.getQty(), update_top_of_book_alloc);
                if (not ask_str_date_time.empty()){
                    rapidjson::Value date_time_textPart;
                    date_time_textPart.SetString(ask_str_date_time.c_str(), update_top_of_book_alloc);
                    ask_quote_object.AddMember("last_update_date_time", date_time_textPart, update_top_of_book_alloc);
                }
                update_top_of_book.AddMember("ask_quote", ask_quote_object, update_top_of_book_alloc);
            }
            else{
                std::cerr << "patch_data invoked with both Bid and Ask empty - dropping the request!" << std::endl;
                return "";
            }
            if (not str_date_time.empty()){
                rapidjson::Value date_time_textPart;
                date_time_textPart.SetString(str_date_time.c_str(), update_top_of_book_alloc);
                update_top_of_book.AddMember("last_update_date_time", date_time_textPart, update_top_of_book_alloc);
            }

            // Stringify the DOM
            rapidjson::StringBuffer buffer;
            rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
            update_top_of_book.Accept(writer);
            const std::string& request_json = buffer.GetString();
            //TODO - Add to logging.trace
            //std::cout << request_json << std::endl;

            request.setContentLength(request_json.length());
            std::ostream &requestStream = session.sendRequest(request);
            requestStream << request_json;
            std::istream& responseStream = session.receiveResponse(response);
            std::stringstream resp_stream;
            Poco::StreamCopier::copyStream(responseStream, resp_stream);
            const std::string &&response_str = resp_stream.str();
            if(response_str.length() > 10 && response_str[2] == '_' && response_str[3] == 'i' &&
            response_str[4] == 'd' && response_str[6] == ':')
            {;}
            else{
                std::cout << "http request failed for uri:" << patch_uri << "response: " << response_str << std::endl;
            }
            return "";
        }

        //return id if successful , empty string if failed - logging done internally
        std::string patch_data(const std::string& top_of_book_db_id,
                               const md_handler::MD_MktOverview &aggregated_mkt_overview){
            const md_handler::MD_LastTrade &aggregated_last_trade_data = aggregated_mkt_overview.getLastTrade();
            try{
                request = Poco::Net::HTTPRequest(Poco::Net::HTTPRequest::HTTP_PATCH, patch_uri);
                request.setContentType("application/json");
                request.add("Accept", "application/json");
                std::string &&last_trade_str_date_time = get_date_time_str_from_milliseconds(aggregated_last_trade_data.getMillisecondsSinceEpoch());

                rapidjson::Document update_top_of_book;
                auto &update_top_of_book_alloc = update_top_of_book.GetAllocator();
                update_top_of_book.SetObject();

                rapidjson::Value id_textPart;
                id_textPart.SetString(top_of_book_db_id.c_str(), update_top_of_book_alloc);
                update_top_of_book.AddMember("_id", id_textPart, update_top_of_book_alloc);

                if (aggregated_mkt_overview.getTotalTradingSecSize() != 0)
                    update_top_of_book.AddMember("total_trading_sec_size", aggregated_mkt_overview.getTotalTradingSecSize(), update_top_of_book_alloc);

                rapidjson::Value last_trade_object(rapidjson::kObjectType);
                last_trade_object.AddMember("px", aggregated_last_trade_data.getPx(), update_top_of_book_alloc);
                last_trade_object.AddMember("qty", aggregated_last_trade_data.getQty(), update_top_of_book_alloc);
                if (not last_trade_str_date_time.empty()){
                    rapidjson::Value date_time_textPart;
                    date_time_textPart.SetString(last_trade_str_date_time.c_str(), update_top_of_book_alloc);
                    last_trade_object.AddMember("last_update_date_time", date_time_textPart, update_top_of_book_alloc);
                }
                update_top_of_book.AddMember("last_trade", last_trade_object, update_top_of_book_alloc);

                //market trade volume is repeated type on top of book (buggy - supress for now)
//                {
//                    rapidjson::Value market_trade_volume_arr(rapidjson::kArrayType);
//
//                    {
//                        rapidjson::Value market_trade_volume_object(rapidjson::kObjectType);
//                        market_trade_volume_object.AddMember("participation_period_last_trade_qty_sum",
//                                                             aggregated_last_trade_data.getLastTradeQtySum(), update_top_of_book_alloc);
//                        market_trade_volume_object.AddMember("applicable_period_seconds", aggregated_last_trade_data.getApplicablePeriodSeconds(), update_top_of_book_alloc);
//                        market_trade_volume_arr.PushBack(market_trade_volume_object, update_top_of_book_alloc);
//                    }
//                    update_top_of_book.AddMember("market_trade_volume", market_trade_volume_arr, update_top_of_book_alloc);
//                }

                if (not last_trade_str_date_time.empty()){
                    rapidjson::Value date_time_textPart;
                    date_time_textPart.SetString(last_trade_str_date_time.c_str(), update_top_of_book_alloc);
                    update_top_of_book.AddMember("last_update_date_time", date_time_textPart, update_top_of_book_alloc);
                }

                // Stringify the DOM
                rapidjson::StringBuffer buffer;
                rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
                update_top_of_book.Accept(writer);
                const std::string& request_json = buffer.GetString();
                //TODO - Add to logging.trace
                //std::cout << request_json << std::endl;

                request.setContentLength(request_json.length());
                std::ostream &requestStream = session.sendRequest(request);
                requestStream << request_json;
                std::istream& responseStream = session.receiveResponse(response);
                std::stringstream resp_stream;
                Poco::StreamCopier::copyStream(responseStream, resp_stream);
                const std::string &&response_str = resp_stream.str();
                if(response_str.length() > 10 && response_str[2] == '_' && response_str[3] == 'i' &&
                   response_str[4] == 'd' && response_str[6] == ':'){
                    ;
                }
                else{
                    std::cout << "http request failed for uri:" << patch_uri << "response: " << response_str << std::endl;
                }
                return "";

            }
            catch (Poco::Exception& e){
                // apparently, you MUST call reset before destroying the session, or you'll crash
                //session.reset();
                std::cerr << "poco lib exception: " << e.what() << std::endl;
            }
            return "";
        }
    };
}

