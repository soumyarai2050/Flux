#pragma once


#include "../../CodeGenProjects/TradeEngine/ProjectGroup/market_data/generated/CppCodec/market_data_mongo_db_codec.h"
#include "../../CodeGenProjects/TradeEngine/ProjectGroup/market_data/generated/CppUtilGen/market_data_key_handler.h"
#include "mongo_db_handler.h"
#include "json_codec.h"

using namespace market_data_handler;

namespace FluxCppCore {

    template <typename RootModelType, typename RootModelListType>
    class MongoDBCodec {

    public:
        explicit MongoDBCodec(std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db_) :
        m_sp_mongo_db_(std::move(sp_mongo_db_)),
        m_max_id_(get_max_id_from_collection()) {}

        int32_t insert(const RootModelType &kr_root_model_type) {
            bsoncxx::builder::basic::document bson_doc;
            prepare_doc(kr_root_model_type, bson_doc);
            auto new_generated_id = get_next_insert_id();
            update_id_in_document(bson_doc, new_generated_id);
            try {
                auto client = m_sp_mongo_db_->get_pool_client();
                mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                auto m_mongo_db_collection_ = db[get_root_model_name()];
                auto insert_result = m_mongo_db_collection_.insert_one(bson_doc.view());
                auto inserted_id = insert_result->inserted_id().get_int32().value;
                assert( new_generated_id == inserted_id);
            } catch (const std::exception& qe) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error while inserting data to collection: {}, document: {}, "
                                                  "error reason: {}", get_root_model_name(),
                                                  bsoncxx::to_json(bson_doc.view()), qe.what());
                new_generated_id = -1;
            }
            return new_generated_id;
        }


        bool insert(bsoncxx::builder::basic::document &r_bson_doc, const std::string &kr_root_model_key,
                    int32_t &r_new_generated_id_out) {
            r_new_generated_id_out = get_next_insert_id();
            update_id_in_document(r_bson_doc, r_new_generated_id_out);
            try {
                auto client = m_sp_mongo_db_->get_pool_client();
                mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                auto m_mongo_db_collection_ = db[get_root_model_name()];
                auto insert_result = m_mongo_db_collection_.insert_one(r_bson_doc.view());
                auto inserted_id = insert_result->inserted_id().get_int32().value;
                m_root_model_key_to_db_id[kr_root_model_key] = r_new_generated_id_out;
                return (inserted_id == r_new_generated_id_out);
            } catch (const std::exception& qe) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error while inserting data to collection: {}, document: {}, "
                                                  "error reason: {}", get_root_model_name(),
                                                  bsoncxx::to_json(r_bson_doc.view()), qe.what());
                r_new_generated_id_out = -1;
                return false;
            }
        }

        int32_t insert_or_update(RootModelType &kr_root_model_obj) {
    	    int32_t r_new_generated_id_out{-1};
            std::string root_model_key;
    	    kr_root_model_obj.set_id(r_new_generated_id_out);
            if(CheckInitializedAndGetKey(kr_root_model_obj, root_model_key)){
        	    insert_or_update(kr_root_model_obj, root_model_key, r_new_generated_id_out);
            }
            return r_new_generated_id_out; // not initialized or missing required fields
        }

        bool insert_or_update(const RootModelType &kr_root_model_obj, const std::string &r_root_model_key,
                              int32_t &r_new_generated_id_out) {
            bsoncxx::builder::basic::document bson_doc{};
            auto found = m_root_model_key_to_db_id.find(r_root_model_key);
            if (found == m_root_model_key_to_db_id.end()) {
                // Key does not exist, so it's a new object. Insert it into the database
                prepare_doc(kr_root_model_obj, bson_doc);
                if (insert(bson_doc, r_root_model_key, r_new_generated_id_out)) {
                    return true;
                }
            } else {
                prepare_doc(kr_root_model_obj, bson_doc);
                if (update_or_patch(found->second, bson_doc)) {
                    r_new_generated_id_out = found->second;
                    return true;
                }
            }
            return false;
        }

        bool bulk_insert(const RootModelListType &kr_root_model_list_obj,
                         const std::vector<std::string> &kr_root_model_key_list,
                         std::vector<int32_t> &r_new_generated_id_list_out) {
            size_t size = kr_root_model_key_list.size();
            std::vector<bsoncxx::builder::basic::document> bson_doc_list;
            bson_doc_list.reserve(size);
            r_new_generated_id_list_out.reserve(size);
            prepare_list_doc(kr_root_model_list_obj, bson_doc_list);
            for (size_t i = 0; i < bson_doc_list.size(); ++i) {
                r_new_generated_id_list_out.push_back(get_next_insert_id());
                update_id_in_document(bson_doc_list[i], r_new_generated_id_list_out[i]);
            }
            mongocxx::stdx::optional<mongocxx::result::insert_many> insert_results;
            {
                auto client = m_sp_mongo_db_->get_pool_client();
                mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                auto m_mongo_db_collection_ = db[get_root_model_name()];
                insert_results = m_mongo_db_collection_.insert_many(bson_doc_list);
            }

            for (size_t i = 0; i < bson_doc_list.size(); ++i) {
                auto inserted_id = insert_results->inserted_ids().at(i).get_int32().value;
                assert(inserted_id == r_new_generated_id_list_out[i]);
                m_root_model_key_to_db_id[kr_root_model_key_list[i]] = r_new_generated_id_list_out[i];
            }

            return insert_results->inserted_count() == static_cast<int32_t>(bson_doc_list.size());
        }

        //Patch the data (update specific document)
        bool patch(const RootModelType &kr_root_model_obj) {
            std::string root_model_key;
            if(CheckInitializedAndGetKey(kr_root_model_obj, root_model_key)){
                return patch(kr_root_model_obj, root_model_key);
            }
            return false; // not initialized or missing required fields
        }

        bool patch(const RootModelType &kr_root_model_obj, const std::string &r_root_model_key) {
            bsoncxx::builder::basic::document bson_doc{};
            if (!r_root_model_key.empty()) {
                prepare_doc(kr_root_model_obj, bson_doc);
                return update_or_patch(m_root_model_key_to_db_id.at(r_root_model_key), bson_doc);
            } else {
                MarketDataKeyHandler::get_key_out(kr_root_model_obj, r_root_model_key);
                auto found = get_db_id_from_key(r_root_model_key, kr_root_model_obj);
                prepare_doc(kr_root_model_obj, bson_doc);
                return update_or_patch(found->second, bson_doc);
            }
        }

        //Patch the data (update specific document) and retrieve the updated object
        bool patch(const RootModelType &kr_root_model_obj, RootModelType &r_root_model_obj_out) {
            std::string root_model_key;
            if(CheckInitializedAndGetKey(kr_root_model_obj, root_model_key)){
                return patch(kr_root_model_obj, r_root_model_obj_out, root_model_key);
            }
            return false; // not initialized or missing required fields
        }

        bool patch(const RootModelType &kr_root_model_obj, RootModelType &r_root_model_obj_out,
                   const std::string &r_root_model_key) {
            bool status = patch(kr_root_model_obj, r_root_model_key);
            if (status) {
                auto r_model_doc_id = m_root_model_key_to_db_id.at(r_root_model_key);
                status = get_data_by_id_from_collection(r_root_model_obj_out, r_model_doc_id);
            }
            return status;
        }

        static bool process_element(const bsoncxx::document::element &element, bsoncxx::builder::basic::document &new_doc) {
            if (element.type() == bsoncxx::type::k_date) {
                auto date_value = element.get_date();
                auto duration_since_epoch = std::chrono::duration_cast<std::chrono::microseconds>(date_value.value);

                std::chrono::system_clock::time_point tp(duration_since_epoch);

                std::time_t tt = std::chrono::system_clock::to_time_t(tp);
                std::tm *gmt = std::localtime(&tt);

                char date_str[256];
                std::strftime(date_str, sizeof(date_str), "%Y-%m-%dT%H:%M:%S", gmt);
                std::string iso_date_str = std::string(date_str) + "+00:00";

                new_doc.append(bsoncxx::builder::basic::kvp(element.key(), iso_date_str));
            } else if (element.type() == bsoncxx::type::k_document) {
                bsoncxx::builder::basic::document inner_doc;
                for (const auto& inner_element : element.get_document().view()) {
                    process_element(inner_element, inner_doc);
                }
                new_doc.append(bsoncxx::builder::basic::kvp(element.key(), inner_doc.view()));
            } else {
                new_doc.append(bsoncxx::builder::basic::kvp(element.key(), element.get_value()));
            }
            return true;
        }

        bool update_or_patch(const int32_t &kr_model_doc_id, const bsoncxx::builder::basic::document &kr_bson_doc) {
            auto update_filter = FluxCppCore::make_document(FluxCppCore::kvp("_id", kr_model_doc_id));
            auto update_document = FluxCppCore::make_document(
                    FluxCppCore::kvp("$set", kr_bson_doc.view()));

            try {
                {
                    auto client = m_sp_mongo_db_->get_pool_client();
                    mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                    auto m_mongo_db_collection_ = db[get_root_model_name()];
                    auto result = m_mongo_db_collection_.update_one(
                        update_filter.view(), update_document.view());
                }

            } catch (const std::exception& qe) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error while updating data to collection: {}, document: {}, "
                                                  "error message: {}", get_root_model_name(),
                                                  bsoncxx::to_json(update_document.view()), qe.what());
                return false;
            }
            return true;
        }

        // Bulk patch the data (update specific documents)
        bool bulk_patch(const RootModelListType &kr_root_model_list_obj) {
            std::vector<bsoncxx::builder::basic::document> bson_doc_list;
            std::vector<std::string> root_model_key_list;
            MarketDataKeyHandler::get_key_list(kr_root_model_list_obj, root_model_key_list);
            std::vector<int32_t> root_model_doc_ids;
            root_model_doc_ids.reserve(root_model_key_list.size());

            for (const auto& key : root_model_key_list) {
                auto found = get_db_id_from_key(key, kr_root_model_list_obj);
                root_model_doc_ids.emplace_back(std::move(found->second));
            }

            prepare_list_doc(kr_root_model_list_obj, bson_doc_list);
            bool status = bulk_update_or_patch_collection(root_model_doc_ids, bson_doc_list);
            return status;
        }

        // Bulk patch the data (update specific documents) and retrieve the updated objects
        bool bulk_patch(const RootModelListType &kr_root_model_list_obj,
                        RootModelListType &r_root_model_list_obj_out) {
            std::vector<bsoncxx::builder::basic::document> bson_doc_list;
            std::vector<std::string> root_model_key_list;
            MarketDataKeyHandler::get_key_list(kr_root_model_list_obj, root_model_key_list);
            std::vector<int32_t> r_model_doc_ids;

            int i = 0;
            for (const auto& root_model_obj : kr_root_model_list_obj) {
                auto found = get_db_id_from_key(root_model_key_list[i], root_model_obj);
                r_model_doc_ids.emplace_back(std::move(found->second));
                ++i;
            }
            prepare_list_doc(kr_root_model_list_obj, bson_doc_list);
            bool status = bulk_update_or_patch_collection(r_model_doc_ids, bson_doc_list);
            if (status) {
                get_all_data_from_collection(r_root_model_list_obj_out);
            } // else not required: Retrieve updated data if the update or patch was successful
            return status;
        }

        bool get_all_data_from_collection(RootModelListType &r_root_model_list_obj_out) {
            try {
                std::string all_data_from_db_json_string;
                auto client = m_sp_mongo_db_->get_pool_client();
                mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                auto m_mongo_db_collection_ = db[get_root_model_name()];
                auto cursor = m_mongo_db_collection_.find({});

                for (const auto &bson_doc : cursor) {
                    bsoncxx::builder::basic::document new_doc;
                    for (const auto &element: bson_doc) {
                        process_element(element, new_doc);
                    }

                    std::string doc_view = bsoncxx::to_json(new_doc.view());
                    size_t pos = doc_view.find("_id");
                    while (pos != std::string::npos) {
                        if (!isalpha(doc_view[pos - 1])) {
                            doc_view.erase(pos, 1);
                        }
                        pos = doc_view.find("_id", pos + 1);
                    }

                    all_data_from_db_json_string += doc_view;
                    all_data_from_db_json_string += ",";
                }

                if (all_data_from_db_json_string.back() == ',') {
                    all_data_from_db_json_string.pop_back();
                } // else not required: all_data_from_db_json_string is empty so need to perform any operation
                r_root_model_list_obj_out.Clear();

                if (!all_data_from_db_json_string.empty())
                    return FluxCppCore::RootModelListJsonCodec<RootModelListType>::decode_model_list(
                        r_root_model_list_obj_out, all_data_from_db_json_string);
            } catch (const std::exception& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error {}, function{}", e.what(), __func__);
            }
            return false;
        }

        bool
        bulk_update_or_patch_collection(const std::vector<int32_t> &kr_model_doc_ids,
                                        const std::vector<bsoncxx::builder::basic::document> &kr_bson_doc_list) {
            auto client = m_sp_mongo_db_->get_pool_client();
            mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
            auto m_mongo_db_collection_ = db[get_root_model_name()];
            auto bulk_write = m_mongo_db_collection_.create_bulk_write();
            for (int i = 0; i < kr_model_doc_ids.size(); ++i) {
                auto update_filter = FluxCppCore::make_document(FluxCppCore::kvp("_id", kr_model_doc_ids[i]));
                auto update_document = FluxCppCore::make_document(
                        FluxCppCore::kvp("$set", kr_bson_doc_list[i]));
                mongocxx::model::update_one updateOne(update_filter.view(), update_document.view());
                updateOne.upsert(false);
                bulk_write.append(updateOne);
            }
            mongocxx::stdx::optional<mongocxx::result::bulk_write> result;

            {
                result = bulk_write.execute();
            }

            if (result) {
                auto modified_count = result->modified_count();
                auto matched_count = result->matched_count();
                return (modified_count == matched_count); // Return true only if all updates were successful
            } else {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Bulk update failed {}", __func__);
                return false;
            }
        }

        bool get_data_by_id_from_collection(RootModelType &r_root_model_obj_out, const int32_t &kr_root_model_doc_id) {
            bool status = false;
            try {
                auto client = m_sp_mongo_db_->get_pool_client();
                mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                auto m_mongo_db_collection_ = db[get_root_model_name()];
                auto cursor = m_mongo_db_collection_.find(
                        bsoncxx::builder::stream::document{} << "_id" << kr_root_model_doc_id << bsoncxx::builder::stream::finalize);
                if (cursor.begin() != cursor.end()) {
                    auto &&doc = *cursor.begin();

                    bsoncxx::builder::basic::document new_doc;
                    for (const auto &element : doc) {
                        process_element(element, new_doc);
                    }

                    std::string new_bson_doc = bsoncxx::to_json(new_doc.view());
                    size_t pos = new_bson_doc.find("_id");
                    while (pos != std::string::npos) {
                        if (!isalpha(new_bson_doc[pos - 1])) {
                            new_bson_doc.erase(pos, 1);
                        }
                        pos = new_bson_doc.find("_id", pos + 1);
                    }

                    status = FluxCppCore::RootModelJsonCodec<RootModelType>::decode_model(r_root_model_obj_out, new_bson_doc);
                }
            } catch (const std::exception& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error {}, function {}", e.what(), __func__);
            }
            return status;
        }

        int64_t count_data_from_collection(const bsoncxx::builder::stream::document &filter) {
            auto client = m_sp_mongo_db_->get_pool_client();
            mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
            auto m_mongo_db_collection_ = db[get_root_model_name()];
            return m_mongo_db_collection_.count_documents({filter});
        }

        int64_t count_data_from_collection() {
            auto client = m_sp_mongo_db_->get_pool_client();
            mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
            auto m_mongo_db_collection_ = db[get_root_model_name()];
            return m_mongo_db_collection_.count_documents({});
        }

        bool delete_all_data_from_collection() {
            mongocxx::stdx::optional<mongocxx::result::delete_result> result;
            {
                auto client = m_sp_mongo_db_->get_pool_client();
                mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                auto m_mongo_db_collection_ = db[get_root_model_name()];
                result = m_mongo_db_collection_.delete_many({});
            }
            return result ? true : false;
        }

        bool delete_all_data_from_collection(const bsoncxx::builder::stream::document &filter) {
            mongocxx::stdx::optional<mongocxx::result::delete_result> result;
            {
                auto client = m_sp_mongo_db_->get_pool_client();
                mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                auto m_mongo_db_collection_ = db[get_root_model_name()];
                result = m_mongo_db_collection_.delete_many({filter});
            }
            return result ? true : false;
        }

        bool delete_data_by_id_from_collection(const int32_t &kr_model_doc_id) {
            mongocxx::stdx::optional<mongocxx::result::delete_result> result;
            {
                auto client = m_sp_mongo_db_->get_pool_client();
                mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                auto m_mongo_db_collection_ = db[get_root_model_name()];
                result = m_mongo_db_collection_.delete_one(
                    bsoncxx::builder::stream::document{} << "_id" << kr_model_doc_id << bsoncxx::builder::stream::finalize);
            }
            return result ? true : false;
        }

        size_t get_md_key_to_db_id_size() const {
            return m_root_model_key_to_db_id.size();
        }

        int32_t get_max_id_from_collection() {
            int32_t max_id = 0;
            auto sort_doc = bsoncxx::builder::stream::document{} << "_id" << -1 << bsoncxx::builder::stream::finalize;
            mongocxx::options::find opts{};
            opts.sort(sort_doc.view());
            opts.limit(1); // Limit to only fetch one document
            auto client = m_sp_mongo_db_->get_pool_client();
            mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
            auto m_mongo_db_collection_ = db[get_root_model_name()];
            auto cursor = m_mongo_db_collection_.find({}, opts);
            for (auto&& doc : cursor) {
                // Get the ID of the last document
                 max_id = doc["_id"].get_int32().value;
            }
            return max_id;
        }

        std::unordered_map<std::string, int32_t> m_root_model_key_to_db_id;

    protected:
        template <typename ProtoModelType>
        auto get_db_id_from_key(const std::string &kr_key, const ProtoModelType &kr_proto_model_obj){
            auto found = m_root_model_key_to_db_id.find(kr_key);
            if (found == m_root_model_key_to_db_id.end()) {
                const std::string error = "Error!" + get_root_model_name() +
                        "key not found in m_root_model_key_to_db_id map;;; r_root_model_obj: "
                        + kr_proto_model_obj.DebugString() + "map: " + KeyToDbIdAsString();
                throw std::runtime_error(error);
            }
            return found;
        }

        std::string KeyToDbIdAsString() const {
            std::string result = "m_root_model_key_to_db_id: ";
            int index = 1;
            for (const auto &entry: m_root_model_key_to_db_id) {
                result += "key " + std::to_string(index) + ":" + entry.first + " ; value " +
                          std::to_string(index) + ":" + std::to_string(entry.second);
                ++index;
            }
            return result;
        }

        auto get_root_model_name() const {
            auto meta_data = root_model_type_.GetMetadata();
            return meta_data.descriptor->name();
        }

        bool IsInitialized(const RootModelType &kr_root_model_obj) const {
            // return true, if the object is initialized and has all the required fields (false otherwise)
            if (!kr_root_model_obj.IsInitialized()) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Required fields is not initialized in {};;; obj: {}",
                          get_root_model_name(), kr_root_model_obj.DebugString());
                return false;
            } else {
                return true;
            }
        }

        bool CheckInitializedAndGetKey(const RootModelType &kr_root_model_obj, std::string &root_model_key_out) const {
            // populate root_model_key_out and return true, if the object is initialized and has all required fields
            if(IsInitialized(kr_root_model_obj)){
                MarketDataKeyHandler::get_key_out(kr_root_model_obj, root_model_key_out);
                return true;
            } else {
				LOG_ERROR_IMPL(GetCppAppLogger(), "kr_root_model_obj is not initialized: {}", kr_root_model_obj.DebugString());
                return false; // false otherwise
            }
        }

        static void update_id_in_document(bsoncxx::builder::basic::document &r_bson_doc, const int32_t new_generated_id) {
            r_bson_doc.append(kvp("_id", new_generated_id));
        }

        int32_t get_next_insert_id() {
            return ++m_max_id_;
        }

        std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
        RootModelType root_model_type_;
        static inline int32_t c_cur_unused_max_id_ = 1;
        int32_t m_max_id_;
    };


}
