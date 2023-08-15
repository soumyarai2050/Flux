#pragma once

#include "../../CodeGenProjects/market_data/generated/CppCodec/market_data_mongo_db_codec.h"
#include "market_data_json_codec.h"

using namespace market_data_handler;

namespace FluxCppCore {

template <typename RootModelType, typename RootModelListType>
    class MongoDBCodec {

    public:
        explicit MongoDBCodec(std::shared_ptr<market_data_handler::MarketData_MongoDBHandler> sp_mongo_db_,
                              quill::Logger *p_logger = quill::get_logger())
                              :m_sp_mongo_db(sp_mongo_db_),
                              m_mongo_db_collection(m_sp_mongo_db->market_data_service_db[get_root_model_name()]),
                              m_p_logger_(p_logger) {}

        bool insert(bsoncxx::builder::basic::document &r_bson_doc, const std::string &root_model_key,
                    int32_t &new_generated_id_out) {
            new_generated_id_out = get_next_insert_id();
            update_id_in_document(r_bson_doc, new_generated_id_out);
            auto insert_result = m_mongo_db_collection.insert_one(r_bson_doc.view());
            auto inserted_id = insert_result->inserted_id().get_int32().value;
            if (inserted_id == new_generated_id_out) {
                m_root_model_key_to_db_id[root_model_key] = new_generated_id_out;
                return true;
            } else {
                return false;
            }
        }

        bool bulk_insert(const RootModelListType &r_root_model_list_obj,
                         const std::vector<std::string> &r_root_model_key_list,
                         std::vector<int32_t> &r_new_generated_id_list_out) {
            size_t size = r_root_model_key_list.size();
            std::vector<bsoncxx::builder::basic::document> bson_doc_list;
            bson_doc_list.reserve(size);
            r_new_generated_id_list_out.reserve(size);
            prepare_list_doc(r_root_model_list_obj, bson_doc_list);
            for (int i = 0; i < bson_doc_list.size(); ++i) {
                r_new_generated_id_list_out.push_back(get_next_insert_id());
                update_id_in_document(bson_doc_list[i], r_new_generated_id_list_out[i]);
            }
            auto insert_results = m_mongo_db_collection.insert_many(bson_doc_list);
            for (int i = 0; i < bson_doc_list.size(); ++i) {
                auto inserted_id = insert_results->inserted_ids().at(i).get_int32().value;
                assert(r_new_generated_id_list_out[i] == inserted_id);  // assert useful - avoids if in release
                m_root_model_key_to_db_id[r_root_model_key_list[i]] = r_new_generated_id_list_out[i];
            }

            if (insert_results->inserted_count() == bson_doc_list.size()) {
                return true;
            } else {
                return false;
            }
        }

        // Insert or update the data
        bool insert_or_update(const RootModelType &r_root_model_obj, int32_t &r_new_generated_id_out) {
            std::string root_model_key;
            if(CheckInitializedAndGetKey(r_root_model_obj, root_model_key)){
                return insert_or_update(r_root_model_obj, root_model_key, r_new_generated_id_out);
            }
            return false; // not initialized or missing required fields
        }

        bool insert_or_update(const RootModelType &r_root_model_obj, std::string &r_root_model_key_in_n_out,
                              int32_t &r_new_generated_id_out) {
            bool status = false;
            bsoncxx::builder::basic::document bson_doc{};

            auto found = m_root_model_key_to_db_id.find(r_root_model_key_in_n_out);
            if (found == m_root_model_key_to_db_id.end()) {
                // Key does not exist, so it's a new object. Insert it into the database
                prepare_doc(r_root_model_obj, bson_doc);
                status = insert(bson_doc, r_root_model_key_in_n_out, r_new_generated_id_out);
            } else {
                // Key already exists, so update the existing object in the database
                prepare_doc(r_root_model_obj, bson_doc);
                status = update_or_patch(found->second, bson_doc);
            }
            return status;
        }

        //Patch the data (update specific document)
        bool patch(const RootModelType &r_root_model_obj) {
            std::string root_model_key;
            if(CheckInitializedAndGetKey(r_root_model_obj, root_model_key)){
                return patch(r_root_model_obj, root_model_key);
            }
            return false; // not initialized or missing required fields
        }

        bool patch(const RootModelType &r_root_model_obj, std::string r_root_model_key_in_n_out) {
            bool status = false;
            bsoncxx::builder::basic::document bson_doc{};
            if (!r_root_model_key_in_n_out.empty()) {
                prepare_doc(r_root_model_obj, bson_doc);
                status = update_or_patch(m_root_model_key_to_db_id.at(r_root_model_key_in_n_out), bson_doc);
            } else {
                MarketDataKeyHandler::get_key_out(r_root_model_obj, r_root_model_key_in_n_out);
                auto found = get_db_id_from_key(r_root_model_key_in_n_out, r_root_model_obj);
                prepare_doc(r_root_model_obj, bson_doc);
                status = update_or_patch(found->second, bson_doc);
            }
            return status;
        }

        //Patch the data (update specific document) and retrieve the updated object
        bool patch(const RootModelType &r_root_model_obj, RootModelType &r_root_model_obj_out) {
            std::string root_model_key;
            if(CheckInitializedAndGetKey(r_root_model_obj, root_model_key)){
                return patch(r_root_model_obj, r_root_model_obj_out, root_model_key);
            }
            return false; // not initialized or missing required fields
        }

        bool patch(const RootModelType &r_root_model_obj, RootModelType &r_root_model_obj_out,
                   std::string &r_root_model_key_in_n_out) {
            bool status = patch(r_root_model_obj, r_root_model_key_in_n_out);
            if (status) {
                auto r_model_doc_id = m_root_model_key_to_db_id.at(r_root_model_key_in_n_out);
                status = get_data_by_id_from_collection(r_root_model_obj_out, r_model_doc_id);
            }
            return status;
        }

        bool update_or_patch(const int32_t &r_model_doc_id, const bsoncxx::builder::basic::document &r_bson_doc) {
            auto update_filter = market_data_handler::make_document(market_data_handler::kvp("_id", r_model_doc_id));
            auto update_document = market_data_handler::make_document(
                    market_data_handler::kvp("$set", r_bson_doc.view()));
            auto result = m_mongo_db_collection.update_one(update_filter.view(), update_document.view());
            if (result->modified_count() > 0) {
                return true;
            } else {
                return false;
            }
        }

        // Bulk patch the data (update specific documents)
        bool bulk_patch(const RootModelListType &r_root_model_list_obj) {
            std::vector<bsoncxx::builder::basic::document> bson_doc_list;
            std::vector<std::string> root_model_key_list;
            MarketDataKeyHandler::get_key_list(r_root_model_list_obj, root_model_key_list);
            std::vector<int32_t> root_model_doc_ids;
            root_model_doc_ids.reserve(root_model_key_list.size());

            for (int i = 0; i < root_model_key_list.size(); ++i) {
                auto found = get_db_id_from_key(root_model_key_list[i], r_root_model_list_obj);
                root_model_doc_ids.emplace_back(std::move(found->second));
            }
            prepare_list_doc(r_root_model_list_obj, bson_doc_list);
            bool status = bulk_update_or_patch_collection(root_model_doc_ids, bson_doc_list);
            return status;
        }

        // Bulk patch the data (update specific documents) and retrieve the updated objects
        bool bulk_patch(const RootModelListType &r_root_model_list_obj,
                        RootModelListType &r_root_model_list_obj_out) {
            std::vector<bsoncxx::builder::basic::document> bson_doc_list;
            std::vector<std::string> root_model_key_list;
            MarketDataKeyHandler::get_key_list(r_root_model_list_obj, root_model_key_list);
            std::vector<int32_t> r_model_doc_ids;

            int i = 0;
            for (const auto& root_model_obj : r_root_model_list_obj) {
                auto found = get_db_id_from_key(root_model_key_list[i], root_model_obj);
                r_model_doc_ids.emplace_back(std::move(found->second));
                ++i;
            }
            prepare_list_doc(r_root_model_list_obj, bson_doc_list);
            bool status = bulk_update_or_patch_collection(r_model_doc_ids, bson_doc_list);
            if (status) {
                get_all_data_from_collection(r_root_model_list_obj_out);
            } // else not required: Retrieve updated data if the update or patch was successful
            return status;
        }

        bool
        bulk_update_or_patch_collection(const std::vector<int32_t> &r_model_doc_ids,
                                        const std::vector<bsoncxx::builder::basic::document> &r_bson_doc_list) {
            auto bulk_write = m_mongo_db_collection.create_bulk_write();
            for (int i = 0; i < r_model_doc_ids.size(); ++i) {
                auto update_filter = market_data_handler::make_document(market_data_handler::kvp("_id", r_model_doc_ids[i]));
                auto update_document = market_data_handler::make_document(
                        market_data_handler::kvp("$set", r_bson_doc_list[i]));
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
            auto cursor = m_mongo_db_collection.find({});

            for (const auto &bson_doc: cursor) {
                std::string doc_view = bsoncxx::to_json(bson_doc);
                size_t pos = doc_view.find("_id");
                if (pos != std::string::npos)
                    doc_view.erase(pos, 1);
                all_data_from_db_json_string += doc_view;
                all_data_from_db_json_string += ",";
            }
            if (all_data_from_db_json_string.back() == ',') {
                all_data_from_db_json_string.pop_back();
            } // else not required: all_data_from_db_json_string is empty so need to perform any operation
            r_root_model_list_obj_out.Clear();
            if (!all_data_from_db_json_string.empty())
                status = FluxCppCore::RootModelListJsonCodec<RootModelListType>::decode_model_list(
                        r_root_model_list_obj_out, all_data_from_db_json_string);
            return status;
        }

        bool get_data_by_id_from_collection(RootModelType &r_root_model_obj_out, const int32_t &r_root_model_doc_id) {
            bool status = false;
            auto cursor = m_mongo_db_collection.find(
                    bsoncxx::builder::stream::document{} << "_id" << r_root_model_doc_id << bsoncxx::builder::stream::finalize);
            if (cursor.begin() != cursor.end()) {
                auto &&doc = *cursor.begin();
                std::string bson_doc = bsoncxx::to_json(doc);
                size_t pos = bson_doc.find("_id");
                if (pos != std::string::npos)
                    bson_doc.erase(pos, 1);
                status = FluxCppCore::RootModelJsonCodec<RootModelType>::decode_model(r_root_model_obj_out, bson_doc);
                return status;
            } else {
                return status;
            }
        }


        bool delete_all_data_from_collection() {
            auto result = m_mongo_db_collection.delete_many({});
            if (result) {
                return true;
            } else {
                return false;
            }
        }

        bool delete_data_by_id_from_collection(const int32_t &r_model_doc_id) {
            auto result = m_mongo_db_collection.delete_one(
                    bsoncxx::builder::stream::document{} << "_id" << r_model_doc_id << bsoncxx::builder::stream::finalize);
            if (result) {
                return true;
            } else {
                return false;
            }
        }

        std::unordered_map<std::string, int32_t> m_root_model_key_to_db_id;

    protected:
        template <typename ProtoModelType>
        auto get_db_id_from_key(const std::string &key, const ProtoModelType &proto_model_obj){
            auto found = m_root_model_key_to_db_id.find(key);
            if (found == m_root_model_key_to_db_id.end()) {
                const std::string error = "Error!" + get_root_model_name() +
                        "key not found in m_root_model_key_to_db_id map;;; r_root_model_obj: "
                        + proto_model_obj.DebugString() + "map: " + KeyToDbIdAsString();
                throw std::runtime_error(error);
            }
            return found;
        }

        std::string KeyToDbIdAsString() {
            std::string result = "m_root_model_key_to_db_id: ";
            int index = 1;
            for (const auto &entry: m_root_model_key_to_db_id) {
                result += "key " + std::to_string(index) + ":" + entry.first + " ; value " +
                          std::to_string(index) + ":" + std::to_string(entry.second);
                ++index;
            }
            return result;
        }

        static auto get_root_model_name() {
            return RootModelType::GetDescriptor()->name();
        }

        bool IsInitialized(const RootModelType &r_root_model_obj) const{
            // return true, if the object is initialized and has all the required fields (false otherwise)
            if (!r_root_model_obj.IsInitialized()) {
                LOG_ERROR(m_p_logger_, "Required fields is not initialized in {} obj: {}",
                          get_root_model_name(), r_root_model_obj.DebugString());
                return false;
            } else {
                return true;
            }
        }

        bool CheckInitializedAndGetKey(const RootModelType &r_root_model_obj, std::string &root_model_key_out) const{
            // populate root_model_key_out and return true, if the object is initialized and has all required fields
            if(IsInitialized(r_root_model_obj)){
                MarketDataKeyHandler::get_key_out(r_root_model_obj, root_model_key_out);
                return true;
            } else {
                return false; // false otherwise
            }
        }

        static void update_id_in_document(bsoncxx::builder::basic::document &bson_doc, const int32_t new_generated_id) {
            bson_doc.append(kvp("_id", new_generated_id));
        }

        static int32_t get_next_insert_id() {
            static std::mutex max_id_mutex;
            std::lock_guard<std::mutex> lk(max_id_mutex);
            m_cur_unused_max_id++;
            return m_cur_unused_max_id -1 ;
        }

        std::shared_ptr<market_data_handler::MarketData_MongoDBHandler> m_sp_mongo_db;
        quill::Logger* m_p_logger_;
        mongocxx::collection m_mongo_db_collection;
        static inline int32_t m_cur_unused_max_id = 1;
    };

}