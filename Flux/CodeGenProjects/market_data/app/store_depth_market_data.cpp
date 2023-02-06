#include <iostream>
#include <sstream>
#include <unordered_map>

#include <bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/json.hpp>
#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>
#include <Poco/Net/HTTPClientSession.h>
#include <Poco/Net/HTTPRequest.h>
#include <Poco/Net/HTTPResponse.h>
#include <Poco/StreamCopier.h>

using bsoncxx::builder::basic::make_array;
using bsoncxx::builder::basic::make_document;
using bsoncxx::builder::basic::kvp;

const std::string host = "127.0.0.1";
const int port = 8000;
const std::string post_uri = "/market_data_tech/create-top_of_book";


// TODO IMPORTANT get UIR, DB-Name and Table-Name from config (quick get-env for now ?)
const std::string db_uri = "mongodb://localhost:27017";
const std::string market_data_db_name = "market_data_tech";
const std::string market_data_history = "MarketDepthHistory";
const std::string market_depth = "MarketDepth";
const std::string top_of_book = "TopOfBook";

//key constants used across classes via constants for consistency
const std::string symbol_key = "symbol";
const std::string position_key = "position";
const std::string side_key = "side";
const std::string qty_key = "qty";
const std::string px_key = "px";
const std::string operation_key = "operation";
const std::string time_key = "time";
const std::string id_key = "_id";
;


class MarketDataTechUIUpdate
{
protected:
    Poco::Net::HTTPClientSession session;
    Poco::Net::HTTPRequest request;
    Poco::Net::HTTPResponse response;
public:
    MarketDataTechUIUpdate() : session(host, port)
    {
        request = Poco::Net::HTTPRequest(Poco::Net::HTTPRequest::HTTP_POST, post_uri);
        request.setContentType("application/json");
        request.add("Accept", "application/json");
    }

    void create_data(int _id, double px_bid, double qty_bid, double px_ask, double qty_ask)
    {

        // todo: error occurs while using time directly from depth doc:
        //  Error: terminate called after throwing an instance of 'bsoncxx::v_noabi::exception'
        //  what():  expected element type k_string

        std::ostringstream bodyStream;
        bodyStream << "{\"_id\": " << _id << ",\"time\": \"" << "2023-02-05T20:41:22.199Z" << "\",";
        bodyStream << "\"bid_quote\": {\"px\": " << px_bid << ",\"qty\": " << qty_bid << "},";
        bodyStream << "\"ask_quote\": {\"px\": " << px_ask << ",\"qty\": " << qty_ask << "}}";
        request.setContentLength(bodyStream.str().length());
        std::ostream& requestStream = session.sendRequest(request);
        requestStream << bodyStream.str();

        std::istream& responseStream = session.receiveResponse(response);
        Poco::StreamCopier::copyStream(responseStream, std::cout);
    }
};

//TODO URGENT: GET MAX ID form DB and cache it to allow for adding new records (especially needed in restart events)
class MarketDataUpdateHolder{
public:
    int32_t position{};
    bsoncxx::stdx::string_view symbol;
    bsoncxx::stdx::string_view side;
    double px{};
    int32_t qty{};
    bsoncxx::stdx::string_view time;
    bsoncxx::stdx::string_view operation;
};

class MongoDB {
public:
    // The mongocxx::instance constructor & destructor initialize / shut-down the driver, thus mongocxx::instance must
    // be created before using the driver must remain alive for as long as the driver is in use
    mongocxx::instance inst{};
    mongocxx::client conn{mongocxx::uri{db_uri}};
    mongocxx::database market_data_db = conn[market_data_db_name];
};


class MarketDataHandler{
public:
    explicit MarketDataHandler(MongoDB &mongo_db_):mongo_db(mongo_db_) {
        // TODO LAZY performance test and see if non-composite symbol only index make a difference in large data set / adding position / depth makes a difference
        // market_depth_collection.create_index(make_document(kvp("symbol", 1)), {});
        market_depth_collection.create_index(make_document(kvp("symbol", 1), kvp("side", 1)),{});
    }

    void handle_md_rt_update(MarketDataUpdateHolder &marketDataUpdateHolder_) {
        // Building position_symbol_key for the md_key_to_pipeline_n_db_id
        std::ostringstream key_builder, update_key_builder;
        key_builder << std::to_string(marketDataUpdateHolder_.position) << "_" << marketDataUpdateHolder_.side <<
                    "_" << marketDataUpdateHolder_.symbol;
        auto position_symbol_key = key_builder.str();

        // build document to insert
        bsoncxx::document::view_or_value market_depth_document = bsoncxx::builder::stream::document{}
                << time_key << marketDataUpdateHolder_.time
                << symbol_key << marketDataUpdateHolder_.symbol
                << side_key << marketDataUpdateHolder_.side
                << qty_key << marketDataUpdateHolder_.qty
                << px_key << marketDataUpdateHolder_.px
                << position_key << marketDataUpdateHolder_.position
                << operation_key << marketDataUpdateHolder_.operation
                << bsoncxx::builder::stream::finalize;


        handle_md_update(position_symbol_key,
                         reinterpret_cast<const std::string &>(marketDataUpdateHolder_.symbol),
                         reinterpret_cast<const std::string &>(marketDataUpdateHolder_.side),
                         market_depth_document);
    }

    void handle_md_update(const std::string &position_symbol_side_key, const std::string &security_id, const std::string &side,
                          bsoncxx::document::view_or_value &market_depth_document) {
        //check if document exists (update) insert otherwise
        auto found = md_key_to_pipeline_n_db_id.find(position_symbol_side_key);
        std::shared_ptr<Pipeline_n_DB_id> ptr_holder;
        if (found == md_key_to_pipeline_n_db_id.end()) {
            // not found - insert new document
            auto market_depth_insert_result = market_depth_collection.insert_one(market_depth_document);
            auto market_depth_id = market_depth_insert_result->inserted_id();
            // find market_depth_id if this symbol exist in DB , else create an empty record for this symbol and store market_depth_id
            mongocxx::cursor top_of_book_cursor = top_of_book_collection.find(make_document(kvp(symbol_key, security_id)));
            bool top_of_book_found = false;
            bsoncxx::types::bson_value::view top_of_book_id;
            for (auto &&top_of_book_obj: top_of_book_cursor) {
                if (!top_of_book_found) {
                    top_of_book_id = top_of_book_obj[id_key].get_value();
                    top_of_book_found = true;
                }
                else {
                    std::cerr << "Error: more than one " << id_key << " entries found in db, previously found: " <<
                    top_of_book_id.get_int32().value << " now found: " << top_of_book_obj[id_key].get_int32().value <<
                    std::endl;
                    return;
                }
            }
            if (!top_of_book_found) {
                // no top of book entry found in DB , create one and get it's id
                // build document to insert
                bsoncxx::document::view_or_value top_of_book_document = bsoncxx::builder::stream::document{}
                        << symbol_key << security_id
                        << bsoncxx::builder::stream::finalize;
                auto top_of_book_insert_result = top_of_book_collection.insert_one(top_of_book_document);
                top_of_book_id = top_of_book_insert_result->inserted_id();
            }
            // pipeline to perform aggregation
            std::shared_ptr<Pipeline_n_DB_id> ptr_Pipeline_n_DB_id( new Pipeline_n_DB_id );
            update_pipeline(ptr_Pipeline_n_DB_id->pipeline, security_id, side);
            ptr_Pipeline_n_DB_id->top_of_book_id = top_of_book_id;
            ptr_Pipeline_n_DB_id->market_depth_id = market_depth_id;
            // store updated pipeline for future reuse
            md_key_to_pipeline_n_db_id[position_symbol_side_key] = ptr_Pipeline_n_DB_id;
            ptr_holder = ptr_Pipeline_n_DB_id;
        }
        else {
            // found - update existing document
            ptr_holder = found->second;
            auto update_filter = make_document(kvp("_id", ptr_holder->market_depth_id));
            auto update_document = make_document(
                    kvp("$set", market_depth_document));
            market_depth_collection.update_one(update_filter.view(), update_document.view());
        }
        // irrespective of inserted or updated - let's aggregate
        auto market_depth_result = market_depth_collection.aggregate(ptr_holder->pipeline, mongocxx::options::aggregate{});
        bool first = true;

        // todo: market_depth_result is empty loop not iterating.
        for(auto&& depth_doc : market_depth_result){
            if (first) {
//                bsoncxx::document::view_or_value top_of_book_document = bsoncxx::builder::stream::document{}
//                        << time_key << depth_doc[time_key].get_value()
//                        << symbol_key << depth_doc[symbol_key].get_value()
//                        //<< side_key << depth_doc[side_key].get_value()
//                        //<< qty_key << depth_doc["size"].get_value()  // store market native size to our qty key
//                        //<< px_key << depth_doc["price"].get_value()  // store market native price to our px key
//                        << bsoncxx::builder::stream::finalize;
//                auto update_filter = make_document(kvp("_id", ptr_holder->top_of_book_id));
//                auto update_document = make_document(
//                        kvp("$set", market_depth_document));
//                top_of_book_collection.update_one(update_filter.view(), top_of_book_document.view());

                 MarketDataTechUIUpdate market_data_tech_ui_update;
                if (std::string (depth_doc[side_key].get_string().value) == "BID"){
                    // todo (reason using hard coded fo argument id): bug terminate called after throwing an instance of 'bsoncxx::v_noabi::exception'
                    //  what():  expected element type k_int32
                    market_data_tech_ui_update.create_data(0,
                                                           depth_doc[px_key].get_double().value,
                                                           depth_doc[qty_key].get_double().value, 0, 0);
                }
                else{
                    market_data_tech_ui_update.create_data(0, 0,
                                                           0, depth_doc[px_key].get_double().value,
                                                           depth_doc[qty_key].get_double().value);
                }
            }else{
                // todo: implement patch in else part need to discuss
            }
            //1. cache the top of the book depth if not cached
            //2. if top of the book different from cached - update cache and post to web API (top-of-book-table)
        }
    }

    void print_id_market_depth_document_map() {
        for (auto &[key, value]: md_key_to_pipeline_n_db_id) {
            std::cout << key << ": " << value->market_depth_id.get_int32().value << std::endl;
        }
    }

protected:
    // creating map to store IDs of the inserted document to use with future updates
    struct Pipeline_n_DB_id{
        // TODO LAZY pipeline and top_of_book_id are one per symbol - optimize to lookup and reference common instance
        mongocxx::pipeline pipeline{};
        bsoncxx::types::bson_value::view top_of_book_id;
        bsoncxx::types::bson_value::view market_depth_id;
    };
    std::unordered_map<std::string, std::shared_ptr<Pipeline_n_DB_id>> md_key_to_pipeline_n_db_id;
    MongoDB &mongo_db;
    // get the market_data_db_name and collection
    mongocxx::collection market_depth_collection = mongo_db.market_data_db[market_depth];
    mongocxx::collection top_of_book_collection = mongo_db.market_data_db[top_of_book];

    static void update_pipeline(mongocxx::pipeline &pipeline, const std::string &security_id, const std::string &side){
        static const std::string dollar_qty_key = "$" + qty_key;
        static const std::string dollar_px_key = "$" + px_key;
        pipeline.append_stage(make_document(
                kvp("$match", make_document(
                        kvp("$and", make_array(make_document(kvp(symbol_key, security_id)), make_document(kvp(side_key, side))))
                ))));
        pipeline.append_stage(make_document(
                kvp("$project", make_document(
                        kvp(operation_key, 0)
                ))));
        pipeline.append_stage(make_document(
                kvp("$setWindowFields", make_document(
                        kvp("sortBy", make_document(
                                kvp(position_key, 1)
                        )),
                        kvp("output", make_document(
                                kvp("cumulative_notional", make_document(
                                        kvp("$sum", make_document(
                                                kvp("$multiply", make_array(dollar_px_key, dollar_qty_key))
                                        )),
                                        kvp("window", make_document(
                                                kvp("documents", make_array("unbounded", "current"))
                                        ))
                                )),
                                kvp("cumulative_qty", make_document(
                                        kvp("$sum", dollar_qty_key),
                                        kvp("window", make_document(
                                                kvp("documents", make_array("unbounded", "current"))
                                        ))
                                ))
                        ))
                ))
        ));
        pipeline.append_stage(make_document(
                kvp("$addFields", make_document(
                        kvp("cumulative_avg_px", make_document(
                                kvp("$divide", make_array("$cumulative_notional", "$cumulative_qty"))
                ))))));

        pipeline.append_stage(make_document(
                kvp("$merge", make_document(
                        kvp("into", market_depth),
                        kvp("on", "_id"),
                        kvp("whenMatched", "replace"),
                        kvp("whenNotMatched", "insert")
                ))
        ));
    }
};

class MarketDataHistoryManager{
public:
    MarketDataHistoryManager(MongoDB &mongo_db_, MarketDataHandler& marketDataHandler_):mongo_db(mongo_db_),
    marketDataHandler(marketDataHandler_){
    }

    void replay(){
        for (auto &&history_document: market_depth_history_cursor) {
            bsoncxx::document::view_or_value market_depth_document = bsoncxx::builder::stream::document{}
                    << time_key << history_document[time_key].get_value()
                    << symbol_key << history_document[symbol_key].get_value()
                    << side_key << history_document[side_key].get_value()
                    << qty_key << history_document[qty_key].get_value()  // store market native size to our qty key
                    << px_key << history_document[px_key].get_value()  // store market native price to our px key
                    << position_key << history_document[position_key].get_value()
                    << operation_key << history_document[operation_key].get_value()
                    << bsoncxx::builder::stream::finalize;

            // Building position_symbol_side_key for the md_key_to_pipeline_n_db_id
            std::ostringstream key_builder, update_key_builder;
            auto symbol = history_document[symbol_key].get_string().value;
            auto position = history_document[position_key].get_int32().value;
            auto side = history_document[side_key].get_string().value;
            key_builder << std::to_string(position) << "_" << side << "_" << symbol;
            auto position_symbol_side_key = key_builder.str();

            marketDataHandler.handle_md_update(position_symbol_side_key,
                                               reinterpret_cast<const std::string &>(history_document[symbol_key].get_string().value),
                                               reinterpret_cast<const std::string &>(history_document[side_key].get_string().value),
                                               market_depth_document);
        }
    }
protected:
    MongoDB &mongo_db;
    MarketDataHandler& marketDataHandler;
    mongocxx::collection market_depth_history_collection{mongo_db.market_data_db[market_data_history]};
    // creating cursor for MarketDepthHistory collection
    mongocxx::cursor market_depth_history_cursor = market_depth_history_collection.find({});
};

int main()
{
    MongoDB mongo_db;
    MarketDataHandler marketDataHandler(mongo_db);
    MarketDataHistoryManager marketDataHistoryManager(mongo_db, marketDataHandler);
    marketDataHistoryManager.replay();
}