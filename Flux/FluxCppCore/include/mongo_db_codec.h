#include "../../CodeGenProjects/market_data/generated/CppCodec/market_data_mongo_db_codec.h"

using namespace market_data_handler;

namespace FluxCppCore {

template <typename RootModelType, typename RootModelListType>
class MongoDBCodec {

    public:
        explicit MongoDBCodec(std::shared_ptr<market_data_handler::MarketData_MongoDBHandler> mongo_db_, mongocxx::collection mongo_db_collection_,
                                            quill::Logger *logger) : mongo_db(mongo_db_), mongo_db_collection(mongo_db_collection_), logger_(logger) {
        }

        /**
         * Insert or update the dash data
        */
        bool insert_or_update(const RootModelType &r_root_model_obj, int32_t &new_generated_id_out) {
            if (!r_root_model_obj.IsInitialized()) {
                LOG_ERROR(logger_, "Reuired fields is not initialized in {} obj: {}",
                          RootModelType::GetDescriptor()->name(), r_root_model_obj.DebugString());
            } // else not required: code continues here for cases where the r_root_model_obj is initialized and has all the required fields
            std::string r_model_key;
            MarketDataKeyHandler::get_key_out(r_root_model_obj, r_model_key);
            bool status = insert_or_update(r_root_model_obj, r_model_key, new_generated_id_out);
            return status;
        }

        bool insert_or_update(const RootModelType &r_root_model_obj, std::string &r_model_key_in_n_out,
                                   int32_t &new_generated_id_out) {
            bool status = false;
            bsoncxx::builder::basic::document bson_doc{};

            auto found = r_model_key_to_db_id.find(r_model_key_in_n_out);
            if (found == r_model_key_to_db_id.end()) {
                // Key does not exist, so it's a new object. Insert it into the database
                prepare_doc(r_root_model_obj, bson_doc);
                status = insert(bson_doc, r_model_key_in_n_out, new_generated_id_out);
            } else {
                // Key already exists, so update the existing object in the database
                prepare_doc(r_root_model_obj, bson_doc);
                status = update_or_patch(found->second, bson_doc);
            }
            return status;
        }

        /**
         * Patch the dash data (update specific document)
        */
        bool patch(const RootModelType &r_root_model_obj) {
            // Check if the object is initialized and has all the required fields
            if (!r_root_model_obj.IsInitialized()) {
                LOG_ERROR(logger_, "Required fields is not initialized in {} obj: {}", 
                          RootModelType::GetDescriptor()->name(), r_root_model_obj.DebugString());
                return false;
            } // else not required: code continues here for cases where the r_root_model_obj is initialized and has all the required fields
            std::string r_model_key;
            MarketDataKeyHandler::get_key_out(r_root_model_obj, r_model_key);
            bool status = patch(r_root_model_obj, r_model_key);
            return status;
        }

        bool patch(const RootModelType &r_root_model_obj, std::string r_model_key_in_n_out) {
            bool status = false;
            bsoncxx::builder::basic::document prepare_list_document{};
            if (!r_model_key_in_n_out.empty()) {
                prepare_doc(r_root_model_obj, prepare_list_document);
                status = update_or_patch(r_model_key_to_db_id.at(r_model_key_in_n_out), prepare_list_document);
            } else {
                MarketDataKeyHandler::get_key_out(r_root_model_obj, r_model_key_in_n_out);
                auto found = r_model_key_to_db_id.find(r_model_key_in_n_out);
                if (found != r_model_key_to_db_id.end()) {
                    prepare_doc(r_root_model_obj, prepare_list_document);
                    status = update_or_patch(found->second, prepare_list_document);
                } else {
                    LOG_ERROR(logger_, "patch failed - {} key not found in r_model_key_to_db_id map;;; {}: {} map: {}",
                              RootModelType::GetDescriptor()->name(), RootModelType::GetDescriptor()->name(), 
                              r_root_model_obj.DebugString(), KeyToDbIdAsString());
                }
            }
            return status;
        }

        /**
         * Patch the dash data (update specific document) and retrieve the updated object
        */
        bool patch(const RootModelType &r_root_model_obj, market_data::Dash &r_root_model_obj_out) {
            // Check if the object is initialized and has all the required fields
            if (!r_root_model_obj.IsInitialized()) {
                LOG_ERROR(logger_, "Required fields is not initialized in {} obj: {}", 
                          RootModelType::GetDescriptor()->name(), r_root_model_obj.DebugString());
                return false;
            } // else not required: code continues here for cases where the r_root_model_obj is initialized and has all the required fields
            std::string r_model_key;
            MarketDataKeyHandler::get_key_out(r_root_model_obj, r_model_key);
            bool status = patch(r_root_model_obj, r_root_model_obj_out, r_model_key);
            return status;
        }

        bool
        patch(const RootModelType &r_root_model_obj, market_data::Dash &r_root_model_obj_out, std::string &r_model_key_in_n_out) {
            bool status = patch(r_root_model_obj, r_model_key_in_n_out);
            if (status) {
                auto r_model_doc_id = r_model_key_to_db_id.at(r_model_key_in_n_out);
                status = get_data_by_id_from_collection(r_root_model_obj_out, r_model_doc_id);
            }
            return status;
        }

        bool update_or_patch(const int32_t &r_model_doc_id, const bsoncxx::builder::basic::document &prepare_list_document) {
            auto update_filter = market_data_handler::make_document(market_data_handler::kvp("_id", r_model_doc_id));
            auto update_document = market_data_handler::make_document(
                    market_data_handler::kvp("$set", prepare_list_document.view()));
            auto result = mongo_db_collection.update_one(update_filter.view(), update_document.view());
            if (result->modified_count() > 0) {
                return true;
            } else {
                return false;
            }
        }

        bool insert(bsoncxx::builder::basic::document &prepare_list_document, const std::string &r_model_key,
                         int32_t &new_generated_id_out) {
            new_generated_id_out = get_next_insert_id();
            update_id_in_document(prepare_list_document, new_generated_id_out);
            auto prepare_list_docinsert_result = mongo_db_collection.insert_one(prepare_list_document.view());
            auto prepare_list_docinserted_id = prepare_list_docinsert_result->inserted_id().get_int32().value;
            assert(prepare_list_docinserted_id == new_generated_id_out);

            if (prepare_list_docinserted_id == new_generated_id_out) {
                r_model_key_to_db_id[r_model_key] = new_generated_id_out;
                return true;
            } else {
                return false;
            }

        }

        bool bulk_insert(const RootModelListType &r_root_model_list_obj, const std::vector<std::string> &r_model_key_list,
                              std::vector<int32_t> &new_generated_id_list_out) {
            std::vector<bsoncxx::builder::basic::document> prepare_list_document_list;
            prepare_list_document_list.reserve(r_root_model_list_obj.prepare_list_docsize());
            new_generated_id_list_out.reserve(r_root_model_list_obj.prepare_list_docsize());
            prepare_list_doc(r_root_model_list_obj, prepare_list_document_list);
            for (int i = 0; i < prepare_list_document_list.size(); ++i) {
                new_generated_id_list_out.emplace_back(std::move(get_next_insert_id()));
                update_id_in_document(prepare_list_document_list[i], new_generated_id_list_out[i]);
            }
            auto prepare_list_docinsert_results = mongo_db_collection.insert_many(prepare_list_document_list);
            for (int i = 0; i < prepare_list_document_list.size(); ++i) {
                auto prepare_list_docinserted_id = prepare_list_docinsert_results->inserted_ids().at(i).get_int32().value;
                assert(new_generated_id_list_out[i] == prepare_list_docinserted_id);
                r_model_key_to_db_id[r_model_key_list[i]] = new_generated_id_list_out[i];
            }

            if (prepare_list_docinsert_results->inserted_count() == prepare_list_document_list.size()) {
                return true;
            } else {
                return false;
            }
        }

        /**
         * Bulk patch the dash data (update specific document)
        */
        bool bulk_patch(const RootModelListType &r_root_model_list_obj) {
            auto size = r_root_model_list_obj.prepare_list_docsize();
            std::vector<bsoncxx::builder::basic::document> prepare_list_document_list;
            prepare_list_document_list.reserve(size);
            std::vector<std::string> r_model_key_list;
            r_model_key_list.reserve(size);
            MarketDataKeyHandler::get_key_list(r_root_model_list_obj, r_model_key_list);
            std::vector<int32_t> r_model_doc_ids;
            r_model_doc_ids.reserve(size);

            for (int i = 0; i < r_root_model_list_obj.prepare_list_docsize(); ++i) {
                if (!r_root_model_list_obj.dash(i).IsInitialized()) {
                    continue;
                } // else not required: code continues here for cases where the r_root_model_obj is initialized and has all the required fields

                auto found = r_model_key_to_db_id.find(r_model_key_list[i]);
                if (found == r_model_key_to_db_id.end()) {
                    const std::string error =
                            "bulk_patch failed - dash key not found in r_model_key_to_db_id map;;; r_root_model_list_obj: " +
                            r_root_model_list_obj.DebugString() + "map: " + KeyToDbIdAsString();
                    throw std::runtime_error(error);
                } else {
                    r_model_doc_ids.emplace_back(std::move(r_model_key_to_db_id.at(r_model_key_list[i])));
                }
            }
            prepare_list_doc(r_root_model_list_obj, prepare_list_document_list);
            bool status = bulk_update_or_patch_collection(r_model_doc_ids, prepare_list_document_list);
            return status;
        }

        /**
         * Bulk patch the dash data (update specific document) and retrieve the updated object
        */
        bool bulk_patch(const RootModelListType &r_root_model_list_obj, market_data::DashList &r_root_model_list_obj_out) {
            auto size = r_root_model_list_obj.prepare_list_docsize();
            std::vector<bsoncxx::builder::basic::document> prepare_list_document_list;
            prepare_list_document_list.reserve(size);
            std::vector<std::string> r_model_key_list;
            r_model_key_list.reserve(size);
            MarketDataKeyHandler::get_key_list(r_root_model_list_obj, r_model_key_list);
            std::vector<int32_t> r_model_doc_ids;
            r_model_doc_ids.reserve(size);

            for (int i = 0; i < r_root_model_list_obj.prepare_list_docsize(); ++i) {
                if (!r_root_model_list_obj.dash(i).IsInitialized())
                    continue;

                auto found = r_model_key_to_db_id.find(r_model_key_list[i]);
                if (found == r_model_key_to_db_id.end()) {
                    const std::string error =
                            "bulk_patch failed - dash key not found in r_model_key_to_db_id map;;; r_root_model_list_obj: " +
                            r_root_model_list_obj.DebugString() + "map: " + KeyToDbIdAsString();
                    throw std::runtime_error(error);
                } else {
                    r_model_doc_ids.emplace_back(std::move(r_model_key_to_db_id.at(r_model_key_list[i])));
                }
            }
            prepare_list_doc(r_root_model_list_obj, prepare_list_document_list);
            bool status = bulk_update_or_patch_collection(r_model_doc_ids, prepare_list_document_list);
            if (status) {
                get_all_data_from_collection(r_root_model_list_obj_out);
            } // else not required: Retrieve updated data if the update or patch was successful
            return status;
        }

        bool bulk_update_or_patch_collection(const std::vector<int32_t> &r_model_doc_ids,
                                                  const std::vector<bsoncxx::builder::basic::document> &prepare_list_document_list) {
            auto bulk_write = mongo_db_collection.create_bulk_write();
            for (int i = 0; i < r_model_doc_ids.size(); ++i) {
                auto update_filter = market_data_handler::make_document(market_data_handler::kvp("_id", r_model_doc_ids[i]));
                auto update_document = market_data_handler::make_document(
                        market_data_handler::kvp("$set", prepare_list_document_list[i]));
                mongocxx::model::update_one updateOne(update_filter.view(), update_document.view());
                updateOne.upsert(false);
                bulk_write.append(updateOne);
            }
            auto result = bulk_write.execute();

            if (result) {
                auto modified_count = result->modified_count();
                auto matched_count = result->matched_count();
                return (modified_count == matched_count); // Return true only if all updates were successful
            } else {
                std::cerr << "Bulk update failed" << std::endl;
                return false;
            }
        }


        bool get_all_data_from_collection(RootModelListType &r_root_model_list_obj_out) {
            bool status = false;
            std::string all_data_from_db_json_string;
            auto cursor = mongo_db_collection.find({});

            for (const auto &prepare_list_docdoc: cursor) {
                std::string prepare_list_docview = bsoncxx::to_json(prepare_list_docdoc);
                size_t pos = prepare_list_docview.find("_id");
                if (pos != std::string::npos)
                    prepare_list_docview.erase(pos, 1);
                all_data_from_db_json_string += prepare_list_docview;
                all_data_from_db_json_string += ",";
            }
            if (all_data_from_db_json_string.back() == ',') {
                all_data_from_db_json_string.pop_back();
            } // else not required: all_data_from_db_json_string is empty so need to perform any operation
            if (!all_data_from_db_json_string.empty())
                status = FluxCppCore::RootModelListJsonCodec<market_data::DashList>::decode_model_list(
                        r_root_model_list_obj_out, all_data_from_db_json_string);
            return status;
        }

        bool get_data_by_id_from_collection(RootModelType &r_root_model_obj_out, const int32_t &r_model_doc_id) {
            bool status = false;
            auto cursor = mongo_db_collection.find(
                    bsoncxx::builder::stream::document{} << "_id" << r_model_doc_id << bsoncxx::builder::stream::finalize);
            if (cursor.begin() != cursor.end()) {
                auto &&doc = *cursor.begin();
                std::string prepare_list_docdoc = bsoncxx::to_json(doc);
                size_t pos = prepare_list_docdoc.find("_id");
                if (pos != std::string::npos)
                    prepare_list_docdoc.erase(pos, 1);
                status = FluxCppCore::RootModelJsonCodec<market_data::Dash>::decode_model(r_root_model_obj_out, prepare_list_docdoc);
                return status;
            } else {
                return status;
            }
        }


        bool delete_all_data_from_collection() {
            auto result = mongo_db_collection.delete_many({});
            if (result) {
                return true;
            } else {
                return false;
            }
        }

    static int32_t get_next_insert_id() {
        std::lock_guard<std::mutex> lk(max_id_mutex);
        cur_unused_max_id++;
        return cur_unused_max_id -1 ;
    }

        bool delete_data_by_id_from_collection(const int32_t &r_model_doc_id) {
            auto result = mongo_db_collection.delete_one(
                    bsoncxx::builder::stream::document{} << "_id" << r_model_doc_id << bsoncxx::builder::stream::finalize);
            if (result) {
                return true;
            } else {
                return false;
            }
        }

        std::string KeyToDbIdAsString() {
            std::string result = "r_model_key_to_db_id: ";
            int index = 1;
            for (const auto &entry: r_model_key_to_db_id) {
                result +=
                        "key " + std::to_string(index) + ":" + entry.first + " ; value " + std::to_string(index) + ":" +
                        std::to_string(entry.second);
                ++index;
            }
            return result;
        }


        static void
        update_id_in_document(bsoncxx::builder::basic::document &prepare_list_document, const int32_t new_generated_id) {
            prepare_list_document.append(kvp("_id", new_generated_id));
        }

        static std::unordered_map<std::string, int32_t> r_model_key_to_db_id;

    protected:
        std::shared_ptr<market_data_handler::MarketData_MongoDBHandler> mongo_db;
        quill::Logger* logger_;
        mongocxx::collection mongo_db_collection;
        static  std::mutex max_id_mutex;
        static int32_t cur_unused_max_id;
    };

    template<>
    std::unordered_map < std::string, int32_t > MongoDBCodec<market_data::Dash, market_data::DashList>::r_model_key_to_db_id;

    template<>
    std::mutex MongoDBCodec<market_data::Dash, market_data::DashList>::max_id_mutex;

    template<>
    int32_t MongoDBCodec<market_data::Dash, market_data::DashList>::cur_unused_max_id;

}