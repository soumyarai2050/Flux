//
// Created by sumit kumar on 16/2/2023.
//

#ifndef MD_HANDLER_MD_DEPTHHANDLER_H
#define MD_HANDLER_MD_DEPTHHANDLER_H

#include "MD_MongoDBHandler.h"

namespace md_handler {
    class MD_DepthHandler {
    public:
        explicit MD_DepthHandler(MD_MongoDBHandler &mongo_db_) : mongo_db(mongo_db_) {
            //build initial cache to avoid duplicate record creation on market depth and top of the book
            // TODO LAZY performance test and see if non-composite symbol only index make a difference in large data set / adding position / depth makes a difference
            // market_depth_collection.create_index(make_document(kvp("symbol", 1)), {});
            market_depth_collection.create_index(
                    bsoncxx::v_noabi::builder::basic::make_document(bsoncxx::v_noabi::builder::basic::kvp("symbol", 1), bsoncxx::v_noabi::builder::basic::kvp("side", 1)), {});

            for (auto&& market_depth_document: market_depth_collection.find({})) {

                std::shared_ptr<Pipeline_n_DB_id> ptr_Pipeline_n_DB_id(new Pipeline_n_DB_id);
                const int8_t position = static_cast<int8_t>(market_depth_document[position_key].get_int32().value);
                const std::string&& symbol = market_depth_document[symbol_key].get_string().value.data();
                const std::string&& side = market_depth_document[side_key].get_string().value.data();
                ptr_Pipeline_n_DB_id->market_depth_id = market_depth_document[id_key].get_value();
                auto position_symbol_side_key = MD_MarketDepth::get_pos_symbol_side_key(position, symbol, side);
                md_key_to_pipeline_n_db_id[position_symbol_side_key] = ptr_Pipeline_n_DB_id;
            }

            for (auto&& top_of_book_document: top_of_book_collection.find({})) {
                std::ostringstream key_builder;
                const std::string&& symbol = top_of_book_document[symbol_key].get_string().value.data();
                const std::string&&  str_id = top_of_book_document[id_key].get_oid().value.to_string();
                top_of_book_publisher.UpdateTopOfBookCache(symbol, str_id);
            }
        }

        void insert_market_depth(const MD_MarketDepth &market_depth_data){
            // build document to insert
            bsoncxx::document::view_or_value market_depth_document = bsoncxx::builder::stream::document{}
                    //<< time_key << marketDataUpdateHolder_.time
                    << symbol_key << market_depth_data.getSymbol()
                    << side_key << market_depth_data.getSide()
                    << qty_key << market_depth_data.getQty()
                    << px_key << market_depth_data.getPx()
                    << position_key << market_depth_data.getPosition() // TODO - Add 64 bit placeholders for cumulative types
                    << time_key << bsoncxx::v_noabi::types::b_date(
                    get_chrono_ms_from_int64(market_depth_data.getMillisecondsSinceEpoch()))
                    << bsoncxx::builder::stream::finalize;

            //check if document exists (update) insert otherwise
            auto found = md_key_to_pipeline_n_db_id.find(market_depth_data.get_position_symbol_side_key());
            std::shared_ptr<Pipeline_n_DB_id> ptr_holder;
            if (found == md_key_to_pipeline_n_db_id.end()) {
                // not found - insert new document
                auto market_depth_insert_result = market_depth_collection.insert_one(market_depth_document);
                auto market_depth_id = market_depth_insert_result->inserted_id();
                // pipeline to perform aggregation
                std::shared_ptr<Pipeline_n_DB_id> ptr_Pipeline_n_DB_id(new Pipeline_n_DB_id);
                update_pipeline(ptr_Pipeline_n_DB_id->pipeline, market_depth_data.getSymbol(), market_depth_data.getSide());
                ptr_Pipeline_n_DB_id->market_depth_id = market_depth_id;
                // store updated pipeline for future reuse
                md_key_to_pipeline_n_db_id[market_depth_data.get_position_symbol_side_key()] = ptr_Pipeline_n_DB_id;
                ptr_holder = ptr_Pipeline_n_DB_id;
            } else {
                // found - update existing document
                ptr_holder = found->second;
                auto update_filter = bsoncxx::v_noabi::builder::basic::make_document(
                        bsoncxx::v_noabi::builder::basic::kvp("_id", ptr_holder->market_depth_id));
                auto update_document = bsoncxx::v_noabi::builder::basic::make_document(
                        bsoncxx::v_noabi::builder::basic::kvp("$set", market_depth_document));
                market_depth_collection.update_one(update_filter.view(), update_document.view());
            }
            // irrespective of inserted or updated - let's aggregate
            auto market_depth_result = market_depth_collection.aggregate(ptr_holder->pipeline,
                                                                         mongocxx::options::aggregate{});
            // The loop just helps commit - without this commit does not trigger - though the code never enters the loop
            // TODO - we may simplify this by getting size or iterator ?
            for (auto &&depth_doc: market_depth_result) {}
        }

        void handle_md_update(const MD_MarketDepth &market_depth_data,
                              const MD_MarketDepth &other_side_market_depth_data = empty_market_depth_data){
            if (market_depth_data.getSide() == "BID")
                handle_md_update_(market_depth_data, other_side_market_depth_data);
            else
                handle_md_update_(other_side_market_depth_data, market_depth_data);
        }

        void handle_md_update_(const MD_MarketDepth &bid_market_depth,
                              const MD_MarketDepth &ask_market_depth)
        {
            if (not bid_market_depth.isEmpty())
                insert_market_depth(bid_market_depth);
            if (not ask_market_depth.isEmpty())
                insert_market_depth(ask_market_depth);


            // Now handle top of book update if this is a top of book update
            std::string dbId;
            if ((not bid_market_depth.isEmpty()) && bid_market_depth.getPosition() == 0){  // only position 0 is top of the book
                // if it's not in cache we create else we update
                dbId = top_of_book_publisher.GetDBIdForSymbol(bid_market_depth.getSymbol());
            }
            else if ((not ask_market_depth.isEmpty()) && ask_market_depth.getPosition() == 0){
                dbId = top_of_book_publisher.GetDBIdForSymbol(ask_market_depth.getSymbol());
            }
            else{
                //no need for top of book update
                return;
            }
            if (dbId.empty()){
                //we create new top of book record
                top_of_book_publisher.create_data(bid_market_depth, ask_market_depth);
            }
            else{ //update existing top of book record
                auto top_of_book_db_id = dbId;
                top_of_book_publisher.patch_data(top_of_book_db_id, bid_market_depth, ask_market_depth);
            }
        }

        void print_id_market_depth_document_map() {
            for (auto &[key, value]: md_key_to_pipeline_n_db_id) {
                std::cout << key << ": " << value->market_depth_id.get_int32().value << std::endl;
            }
        }

        size_t get_md_key_to_pipeline_n_db_id_size() {
            return md_key_to_pipeline_n_db_id.size();
        }

    protected:
        MD_TopOfBookPublisher top_of_book_publisher;
        // creating map to store IDs of the inserted document to use with future updates
        struct Pipeline_n_DB_id {
            // TODO LAZY pipeline and top_of_book_id are one per symbol - optimize to lookup and reference common instance
            mongocxx::pipeline pipeline{};
            bsoncxx::types::bson_value::view top_of_book_id;
            bsoncxx::types::bson_value::view market_depth_id;
        };
        std::unordered_map<std::string, std::shared_ptr<Pipeline_n_DB_id>> md_key_to_pipeline_n_db_id;

        typedef std::unordered_map<std::string, std::string>::iterator top_of_book_cache_itr_type;
        MD_MongoDBHandler &mongo_db;
        // get the market_data_db_name and collection
        mongocxx::collection market_depth_collection = mongo_db.market_data_db[market_depth];
        mongocxx::collection top_of_book_collection = mongo_db.market_data_db[top_of_book];

        static void
        update_pipeline(mongocxx::pipeline &pipeline, const std::string &security_id, const std::string &side) {
            static const std::string dollar_qty_key = "$" + qty_key;
            static const std::string dollar_px_key = "$" + px_key;
            pipeline.append_stage(bsoncxx::v_noabi::builder::basic::make_document(
                    bsoncxx::v_noabi::builder::basic::kvp("$match", bsoncxx::v_noabi::builder::basic::make_document(
                            bsoncxx::v_noabi::builder::basic::kvp("$and", bsoncxx::v_noabi::builder::basic::make_array(
                                    bsoncxx::v_noabi::builder::basic::make_document(
                                            bsoncxx::v_noabi::builder::basic::kvp(symbol_key, security_id)),
                                    bsoncxx::v_noabi::builder::basic::make_document(
                                            bsoncxx::v_noabi::builder::basic::kvp(side_key, side))))
                    ))));
            pipeline.append_stage(bsoncxx::v_noabi::builder::basic::make_document(
                    bsoncxx::v_noabi::builder::basic::kvp("$project", bsoncxx::v_noabi::builder::basic::make_document(
                            bsoncxx::v_noabi::builder::basic::kvp(operation_key, 0)
                    ))));
            pipeline.append_stage(bsoncxx::v_noabi::builder::basic::make_document(
                    bsoncxx::v_noabi::builder::basic::kvp("$setWindowFields", bsoncxx::v_noabi::builder::basic::make_document(
                            bsoncxx::v_noabi::builder::basic::kvp("partitionBy", bsoncxx::v_noabi::builder::basic::make_document(
                                    bsoncxx::v_noabi::builder::basic::kvp("symbol", "$symbol"),
                                    bsoncxx::v_noabi::builder::basic::kvp("side", "$side")
                            )),
                            bsoncxx::v_noabi::builder::basic::kvp("sortBy", bsoncxx::v_noabi::builder::basic::make_document(
                                    bsoncxx::v_noabi::builder::basic::kvp("position", 1)
                            )),
                            bsoncxx::v_noabi::builder::basic::kvp("output", bsoncxx::v_noabi::builder::basic::make_document(
                                    bsoncxx::v_noabi::builder::basic::kvp("cumulative_notional", bsoncxx::v_noabi::builder::basic::make_document(
                                            bsoncxx::v_noabi::builder::basic::kvp("$sum", bsoncxx::v_noabi::builder::basic::make_document(
                                                    bsoncxx::v_noabi::builder::basic::kvp("$multiply", bsoncxx::v_noabi::builder::basic::make_array(dollar_px_key, dollar_qty_key))
                                            )),
                                            bsoncxx::v_noabi::builder::basic::kvp("window", bsoncxx::v_noabi::builder::basic::make_document(
                                                    bsoncxx::v_noabi::builder::basic::kvp("documents", bsoncxx::v_noabi::builder::basic::make_array("unbounded", "current"))
                                            ))
                                    )),
                                    bsoncxx::v_noabi::builder::basic::kvp("cumulative_qty", bsoncxx::v_noabi::builder::basic::make_document(
                                            bsoncxx::v_noabi::builder::basic::kvp("$sum", dollar_qty_key),
                                            bsoncxx::v_noabi::builder::basic::kvp("window", bsoncxx::v_noabi::builder::basic::make_document(
                                                    bsoncxx::v_noabi::builder::basic::kvp("documents", bsoncxx::v_noabi::builder::basic::make_array("unbounded", "current"))
                                            ))
                                    ))
                            ))
                    ))
            ));

            pipeline.append_stage(bsoncxx::v_noabi::builder::basic::make_document(
                    bsoncxx::v_noabi::builder::basic::kvp("$addFields", bsoncxx::v_noabi::builder::basic::make_document(
                            bsoncxx::v_noabi::builder::basic::kvp("cumulative_avg_px", bsoncxx::v_noabi::builder::basic::make_document(
                                    bsoncxx::v_noabi::builder::basic::kvp("$divide", bsoncxx::v_noabi::builder::basic::make_array("$cumulative_notional", "$cumulative_qty"))
                            ))
                    ))
            ));


            pipeline.append_stage(bsoncxx::v_noabi::builder::basic::make_document(
                    bsoncxx::v_noabi::builder::basic::kvp("$merge", bsoncxx::v_noabi::builder::basic::make_document(
                            bsoncxx::v_noabi::builder::basic::kvp("into", market_depth),
                            bsoncxx::v_noabi::builder::basic::kvp("on", "_id"),
                            bsoncxx::v_noabi::builder::basic::kvp("whenMatched", "replace"),
                            bsoncxx::v_noabi::builder::basic::kvp("whenNotMatched", "insert")
                    ))
            ));
        }
    };
}

#endif //MD_HANDLER_MD_DEPTHHANDLER_H
