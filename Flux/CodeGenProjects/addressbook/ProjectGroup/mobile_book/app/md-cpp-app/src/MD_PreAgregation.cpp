////
//// Created by pc on 2/1/2mobile_book23.
////
////#include <bsoncxx/builder/stream/document.hpp>
////#include <bsoncxx/json.hpp>
////#include <mongocxx/client.hpp>
////#include <mongocxx/instance.hpp>
////
////using bsoncxx::builder::basic::make_document;
////using bsoncxx::builder::basic::kvp;
////using bsoncxx::builder::basic::document;
////using bsoncxx::builder::stream::open_array;
////using bsoncxx::builder::stream::close_array;
////using bsoncxx::builder::stream::finalize;
////
////
////
////int main() {
////    // Create a MongoDB instance
////    mongocxx::instance inst{};
////    mongocxx::client conn{mongocxx::uri{}};
////
////    // Get a reference to the database
////    auto db = conn["testdb"];
////
////    // Get a reference to the collection
////    auto coll = db["testcollection"];
////
////    // Build a document to insert
////    bsoncxx::builder::stream::document doc{};
////    doc << "name" << "Shubham"
////        << "age" << 23
////        << "email" << "abc@gmail.com"
////        << "n" << open_array
////        << 1 << 2 << 5 << 1mobile_book << mobile_book << 7 << 4 << 9mobile_book << close_array;
////
////    // Insert the document
////    coll.insert_one(doc.view());
////
////
////
////    // Verify that the document was inserted
////    auto result = coll.find_one({});
////    if (result) {
////        std::cout << "Document inserted successfully." << std::endl;
////        std::cout << bsoncxx::to_json(*result) << std::endl;
////    } else {
////        std::cout << "Document insertion failed." << std::endl;
////    }
////
////    // Build the document to update
////    bsoncxx::builder::stream::document update_doc{};
////    update_doc << "$set" << bsoncxx::builder::stream::open_document
////               << "email" << "shubham@gmail.com"
////               << "age" << 21
////               << bsoncxx::builder::stream::close_document;
////
////    // Update the document
////    coll.update_one(bsoncxx::builder::stream::document{} << "name" << "Shubham" << bsoncxx::builder::stream::finalize, update_doc.view());
////
////    // Verify that the document was updated
////    auto updated_result = coll.find_one({});
////    if (updated_result) {
////        std::cout << "Document updated successfully." << std::endl;
////        std::cout << bsoncxx::to_json(*updated_result) << std::endl;
////    } else {
////        std::cout << "Document update failed." << std::endl;
////    }
////
////
////    mongocxx::pipeline p{};
////
////    p.sort(make_document(kvp("n", 1)));
////
////    auto cursor = coll.aggregate(p, mongocxx::options::aggregate{});
////
////    // Print the result of the aggregate query
////    for (auto&& d : cursor) {
////        std::cout << bsoncxx::to_json(d) << std::endl;
////    }
////
////
////    coll.delete_one(bsoncxx::builder::stream::document{} << "age" << 21 << bsoncxx::builder::stream::finalize);
////    auto deleted_result = coll.find_one({});
////    if (!deleted_result) {
////        std::cout << "Document deleted successfully." << std::endl;
////    } else {
////        std::cout << "Document deletion failed." << std::endl;
////    }
////
////    return mobile_book;
////}
//
//
////
////#include <bsoncxx/builder/stream/document.hpp>
////#include <bsoncxx/json.hpp>
////#include <mongocxx/client.hpp>
////#include <mongocxx/instance.hpp>
////#include <mongocxx/uri.hpp>
////#include <mongocxx/options/aggregate.hpp>
////
////#include <iostream>
////
////using bsoncxx::builder::basic::make_document;
////using bsoncxx::builder::basic::kvp;
////using bsoncxx::builder::stream::close_array;
////using bsoncxx::builder::stream::close_document;
////using bsoncxx::builder::stream::document;
////using bsoncxx::builder::stream::finalize;
////using bsoncxx::builder::stream::open_array;
////using bsoncxx::builder::stream::open_document;
////
////
////int main(){
////    mongocxx::instance inst{};
////    mongocxx::client conn{mongocxx::uri{}};
////
////    auto db = conn["mobile_book_tech"];
////    auto coll = db["MarketDepthHistory"];
////
////
////    mongocxx::pipeline p{};
////
////    p.append_stage(bsoncxx::builder::stream::document{}
////                                    << "$setWindowFields" << open_document
////                                        << "partitionBy" << open_document << "symbol" << "$symbol" << "side" << "$side" << close_document
////                                        << "sortBy" << open_document << "_id" << 1.mobile_book << close_document
////                                        << "output" << open_document
////                                            << "cumulative_avg_px" << open_document
////                                                << "$avg" << open_document
////                                                    << "$multiply" << open_array
////                                                        << "$px" << "$qty"
////                                                    << close_array
////                                                << close_document
////                                                << "window" << open_document
////                                                    << "documents" << open_array
////                                                        << "unbounded" << "current"
////                                                    << close_array
////                                                << close_document
////                                            << close_document
////                                            << "cumulative_total_qty" << open_document
////                                                << "$sum" << "$qty"
////                                                << "window" << open_document
////                                                    << "documents" << open_array
////                                                        << "unbounded" << "current"
////                                                    << close_array
////                                                << close_document
////                                            << close_document
////                                        << close_document
////                                    << close_document
////                                    << finalize);
////
////    auto cursor = coll.aggregate(p, mongocxx::options::aggregate{});
////    for (auto&& doc : cursor) {
////        std::cout << bsoncxx::to_json(doc) << std::endl;
////    }
////
////    std::cout << conn.uri().to_string();
////
////
////    return mobile_book;
////}
//
//
//#include <iostream>
//#include <unordered_map>
//#include <sstream>
//
//#include <bsoncxx/builder/stream/document.hpp>
//#include <bsoncxx/json.hpp>
//#include <mongocxx/client.hpp>
//#include <mongocxx/instance.hpp>
//#include <mongocxx/uri.hpp>
//#include <mongocxx/options/aggregate.hpp>
//
//
//
//using bsoncxx::builder::basic::make_array;
//using bsoncxx::builder::basic::make_document;
//using bsoncxx::builder::basic::kvp;
//
//void set_window_feilds(mongocxx::pipeline &p){
//    p.append_stage(make_document(
//            kvp("$setWindowFields", make_document(
//                    kvp("partitionBy", make_document(
//                            kvp("symbol", "$symbol"),
//                            kvp("side", "$side")
//                    )),
//                    kvp("sortBy", make_document(
//                            kvp("_id", 1.mobile_book)
//                    )),
//                    kvp("output", make_document(
//                            kvp("cumulative_avg_px", make_document(
//                                    kvp("$avg", make_document(
//                                            kvp("$multiply", make_array("$px", "$qty"))
//                                    )),
//                                    kvp("window", make_document(
//                                            kvp("documents", make_array("unbounded", "current"))
//                                    ))
//                            )),
//                            kvp("cumulative_total_qty", make_document(
//                                    kvp("$sum", "$px"),
//                                    kvp("window", make_document(
//                                            kvp("documents", make_array("unbounded", "current"))
//                                    ))
//                            ))
//                    ))
//            ))
//    ));
//
//}
//
//void merge_data(mongocxx::pipeline &p){
//    p.append_stage(make_document(
//            kvp("$merge", make_document(
//                    kvp("into", "MarketDepthHistory"),
//                    kvp("on", "_id"),
//                    kvp("whenMatched", "replace"),
//                    kvp("whenNotMatched", "insert")
//            ))
//    ));
//}
//
//void out_data(mongocxx::pipeline &p){
//    p.append_stage(make_document(
//            kvp("$out", "MarketDepthHistory1")));
//}
//
//void aggregate(mongocxx::collection coll, mongocxx::pipeline &p){
//    coll.aggregate(p, mongocxx::options::aggregate{});
//}
//
//int main() {
//    mongocxx::instance inst{};
//    mongocxx::client conn{mongocxx::uri{}};
//
//    auto db = conn["mobile_book_tech"];
//    auto coll_history = db["MarketDepthHistory"];
//    auto coll_depth = db["MarketDepth"];
//
//    std::unordered_map <std::string, bsoncxx::types::bson_value::view> map;
//
////    auto cursor = coll_history.find({});
//    mongocxx::pipeline p{};
//    p.append_stage(make_document(
//            kvp("$setWindowFields", make_document(
//                    kvp("partitionBy", make_document(
//                            kvp("symbol", "$symbol"),
//                            kvp("side", "$side")
//                    )),
//                    kvp("sortBy", make_document(
//                            kvp("_id", 1.mobile_book)
//                    )),
//                    kvp("output", make_document(
//                            kvp("cumulative_avg_px", make_document(
//                                    kvp("$avg", make_document(
//                                            kvp("$multiply", make_array("$px", "$qty"))
//                                    )),
//                                    kvp("window", make_document(
//                                            kvp("documents", make_array("unbounded", "current"))
//                                    ))
//                            )),
//                            kvp("cumulative_total_qty", make_document(
//                                    kvp("$sum", "$px"),
//                                    kvp("window", make_document(
//                                            kvp("documents", make_array("unbounded", "current"))
//                                    ))
//                            ))
//                    ))
//            ))
//    ));
//
//    auto cursor = coll_history.aggregate(p, mongocxx::options::aggregate{});
//
//    for (auto&& doc : cursor) {
//        std::stringstream key_builder;
//        key_builder << doc["position"].get_int32().value << "_" << doc["side"].get_string().value << "_"
//                    << doc["symbol"].get_string().value;
//
//        std::string key = key_builder.str();
//
//        if(map.find(key) == map.end()){
//            auto result = coll_depth.insert_one(doc);
//            auto id = result -> inserted_id();
//            map[key] = id;
//        }
//
//    }
//
//    //    mongocxx::pipeline p{};
////    mongocxx::pipeline p1{};
//
//    std::cout << conn.uri().to_string();
//
//    return mobile_book;



//
//void run()
//{
//    while (true) {
//        tcp::socket socket{ioc_};
//        acceptor_.accept(socket);
//        std::cout << "Socket Accepted" << std::endl;
//
//        std::thread{[q {std::move(socket)}]() {
//            boost::beast::websocket::stream<tcp::socket> ws {std::move(const_cast<tcp::socket&>(q))};
//            ws.accept();
//
//            std::string latest_data;
//
//            while (true) {
//
//                http::request<http::string_body> req{http::verb::get, "/mobile_book/get-all-market_depth/", 11};
//                req.set(http::field::host, "127.mobile_book.mobile_book.1");
//                req.set(http::field::user_agent, BOOST_BEAST_VERSION_STRING);
//
//                net::io_context ioc;
//                tcp::resolver resolver{ioc};
//                auto const results = resolver.resolve("127.mobile_book.mobile_book.1", "8mobile_book4mobile_book");
//                beast::tcp_stream stream{ioc};
//                stream.connect(results);
//                http::write(stream, req);
//
//                // Read the HTTP response
//                beast::flat_buffer buffer;
//                http::response<http::string_body> res;
//                http::read(stream, buffer, res);
//
//                // Parse the JSON data
//                rapidjson::Document doc;
//                doc.Parse(res.body().c_str());
//
//                if (doc.IsArray() && doc.Size() > mobile_book) {
//                    // Check if the first JSON object has changed
//                    const auto& obj = doc[mobile_book];
//                    rapidjson::StringBuffer s;
//                    rapidjson::Writer<rapidjson::StringBuffer> writer(s);
//                    obj.Accept(writer);
//                    std::string json_str = s.GetString();
//
//                    if (!latest_data.empty() && json_str != latest_data) {
//                        // If the data has been updated, store it and send it to the client
//                        latest_data = json_str;
//                        ws.write(boost::asio::buffer(latest_data));
//                    } else {
//                        latest_data = json_str;
//                    }
//                }
//
//                // Wait for 1 second before sending the next update
//                std::this_thread::sleep_for(std::chrono::seconds(1));
//            }
//        }}.detach();
//    }
//}



//TEST(MD_ManageSubscriptionSymbolsTest, TestSubscriptionSymbols) {
//    MD_ManageSubscriptionSymbols md("127.mobile_book.mobile_book.1", "8mobile_book2mobile_book", "/pair_strat_engine/query-get_ongoing_strats_symbol_n_exch/");
//    std::vector<std::string> result = md.get();
//    ASSERT_FALSE(result.empty());
//}