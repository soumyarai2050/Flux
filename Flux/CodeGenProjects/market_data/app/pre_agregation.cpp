////
//// Created by pc on 2/1/2023.
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
////        << 1 << 2 << 5 << 10 << 0 << 7 << 4 << 90 << close_array;
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
////    return 0;
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
////    auto db = conn["market_data_tech"];
////    auto coll = db["MarketDepthHistory"];
////
////
////    mongocxx::pipeline p{};
////
////    p.append_stage(bsoncxx::builder::stream::document{}
////                                    << "$setWindowFields" << open_document
////                                        << "partitionBy" << open_document << "symbol" << "$symbol" << "side" << "$side" << close_document
////                                        << "sortBy" << open_document << "_id" << 1.0 << close_document
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
////    return 0;
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
//                            kvp("_id", 1.0)
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
//    auto db = conn["market_data_tech"];
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
//                            kvp("_id", 1.0)
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
//    return 0;
//}
