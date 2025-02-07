#pragma once

#include "mongo_db_handler.h"
#include "project_includes.h"
#include "cpp_app_logger.h"

#include <mongocxx/exception/exception.hpp>

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
            auto new_generated_id = kr_root_model_type.id_;
            update_id_in_document(bson_doc, new_generated_id);
            try {
                auto client = m_sp_mongo_db_->get_pool_client();
                mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                auto m_mongo_db_collection_ = db[get_root_model_name()];
                auto insert_result = m_mongo_db_collection_.insert_one(bson_doc.view());
                auto inserted_id = insert_result->inserted_id().get_int32().value;
                if (new_generated_id == inserted_id) {
                    return new_generated_id;
                } else {
                    LOG_WARNING_IMPL(GetCppAppLogger(), "Some error occured while inserting: {};;; doc: {}",
                        get_root_model_name(), bsoncxx::to_json(bson_doc.view()));
                    return -1;
                }
            } catch (const mongocxx::exception& qe) {
                if (qe.code().value() == 11000) {
                    // Extract the `_id` from the error message
                    std::string error_message = qe.what();
                    std::string duplicate_key = "dup key: { _id: ";
                    size_t start_pos = error_message.find(duplicate_key);
                    int extracted_id = -1;

                    if (start_pos != std::string::npos) {
                        start_pos += duplicate_key.size();
                        size_t end_pos = error_message.find(" }", start_pos);
                        if (end_pos != std::string::npos) {
                            std::string id_str = error_message.substr(start_pos, end_pos - start_pos);
                            extracted_id = std::stoi(id_str); // Convert to integer
                        }
                    }

                    RootModelType root_model_obj;
                    get_data_by_id_from_collection(root_model_obj, extracted_id);
                    boost::json::object json_obj;
                    if (MarketDataObjectToJson::object_to_json(root_model_obj, json_obj)) {
                        std::string err_msg = std::format(
                            "Error while inserting data to collection: {}, _id: {} document: {}, "
                            "existing document: {};;; error reason: {}",
                            get_root_model_name(), new_generated_id, bsoncxx::to_json(bson_doc.view()),
                            boost::json::serialize(json_obj), qe.what()
                        );
                        LOG_ERROR_IMPL(GetCppAppLogger(), err_msg);
                    }
                } else {
                    std::string err_msg = std::format(
                        "Error while inserting data to collection: {}, _id: {} document: {};;; error reason: {}",
                        get_root_model_name(), new_generated_id, bsoncxx::to_json(bson_doc.view()), qe.what()
                    );
                    LOG_ERROR_IMPL(GetCppAppLogger(), err_msg);
                }
                new_generated_id = -1;
            }
            return -1;
        }


        bool insert(bsoncxx::builder::basic::document &r_bson_doc, const std::string &kr_root_model_key,
                    int32_t &r_new_generated_id_out) {
            // r_new_generated_id_out = get_next_insert_id();
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
                RootModelType root_model_obj;
                get_data_by_id_from_collection(root_model_obj, r_new_generated_id_out);
                boost::json::object json_obj;
                if (MarketDataObjectToJson::object_to_json(root_model_obj, json_obj)) {
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Error while inserting data to collection: {}, _id: {} document: {}, "
                                                  "existing document: {};;; error reason: {}", get_root_model_name(),
                                                  r_new_generated_id_out, bsoncxx::to_json(r_bson_doc.view()),
                                                  boost::json::serialize(json_obj), qe.what());
                    r_new_generated_id_out = -1;
                }
                return false;
            }
        }

        int32_t insert_or_update(const RootModelType &kr_root_model_obj) {
    	    int32_t r_new_generated_id_out{-1};
            std::string root_model_key;
    	    r_new_generated_id_out = kr_root_model_obj.id_;
            MarketDataKeyHandler::get_key_out(kr_root_model_obj, root_model_key);
        	insert_or_update(kr_root_model_obj, root_model_key, r_new_generated_id_out);
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
                if (inserted_id != r_new_generated_id_list_out[i]) {
                    LOG_ERROR_IMPL(GetCppAppLogger(), "Mismatch in inserted ID: Expected {}, but got {}. Key: {}",
                        r_new_generated_id_list_out[i], inserted_id, kr_root_model_key_list[i]);
                }
                m_root_model_key_to_db_id[kr_root_model_key_list[i]] = r_new_generated_id_list_out[i];
            }

            return insert_results->inserted_count() == static_cast<int32_t>(bson_doc_list.size());
        }

        //Patch the data (update specific document)
        bool patch(const RootModelType &kr_root_model_obj) {
            std::string root_model_key;
            MarketDataKeyHandler::get_key_out(kr_root_model_obj, root_model_key);
            return patch(kr_root_model_obj, root_model_key);
        }

        bool patch(const RootModelType &kr_root_model_obj, std::string &r_root_model_key) {
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
            MarketDataKeyHandler::get_key_out(kr_root_model_obj, root_model_key);
            return patch(kr_root_model_obj, r_root_model_obj_out, root_model_key);
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

        int32_t get_db_id_from_root_model_obj(const RootModelType &kr_root_model_obj) {
            std::string root_model_key;
            MarketDataKeyHandler::get_key_out(kr_root_model_obj, root_model_key);
            auto found = m_root_model_key_to_db_id.find(root_model_key);
            if (found == m_root_model_key_to_db_id.end()) {
                return -1;
            } else {
                return found->second;
            }
        }

        void update_root_model_key_to_db_id(const RootModelType &kr_root_model_obj) {
            std::string root_model_key;
            MarketDataKeyHandler::get_key_out(kr_root_model_obj, root_model_key);
            m_root_model_key_to_db_id[root_model_key] = kr_root_model_obj.id_;
        }

        static bool process_element(const bsoncxx::document::element &element, bsoncxx::builder::basic::document &new_doc) {
            if (element.type() == bsoncxx::type::k_date) {
                auto date_value = element.get_date().value;

                // auto duration_since_epoch = std::chrono::duration_cast<std::chrono::microseconds>(date_value.value);
                //
                // std::chrono::system_clock::time_point tp(duration_since_epoch);
                // std::string iso_date_str = date::format("%FT%T%z", tp);
                //
                new_doc.append(bsoncxx::builder::basic::kvp(element.key(), date_value.count()));
            } else if (element.type() == bsoncxx::type::k_document) {
                bsoncxx::builder::basic::document inner_doc;
                auto documet = element.get_document();
                for (const auto& inner_element : documet.view()) {
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
                    if (result->modified_count() > 0) {
                        return true;
                    } else {
                        return false;
                    }
                }

            } catch (const std::exception& qe) {
                auto err = std::format("Error while updating data to collection: {}, _id: {}, document: {}, "
                                                  "error message: {}", get_root_model_name(), kr_model_doc_id,
                                                  bsoncxx::to_json(update_document.view()), qe.what());
                LOG_ERROR_IMPL(GetCppAppLogger(), err);
                return false;
            }
        }

        bool patch(const int32_t &kr_model_doc_id, const boost::json::object &kr_json_object) const {
            auto update_filter = FluxCppCore::make_document(FluxCppCore::kvp("_id", kr_model_doc_id));
            auto update_document = FluxCppCore::make_document(
                    FluxCppCore::kvp("$set", bsoncxx::from_json(boost::json::serialize(kr_json_object))));

            try {
                {
                    auto client = m_sp_mongo_db_->get_pool_client();
                    mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                    auto m_mongo_db_collection_ = db[get_root_model_name()];
                    auto result = m_mongo_db_collection_.update_one(
                        update_filter.view(), update_document.view());

                    return result->modified_count() > 0;
                }

            } catch (const std::exception& qe) {
                auto err = std::format("Error while updating data to collection: {}, _id: {}, document: {}, "
                                                  "error message: {}", get_root_model_name(), kr_model_doc_id,
                                                  bsoncxx::to_json(update_document.view()), qe.what());
                LOG_ERROR_IMPL(GetCppAppLogger(), err);
                return false;
            }
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
                all_data_from_db_json_string += "[";
                for (const auto &bson_doc : cursor) {
                    bsoncxx::builder::basic::document new_doc;
                    for (const auto &element: bson_doc) {
                        process_element(element, new_doc);
                    }

                    std::string doc_view = bsoncxx::to_json(new_doc.view());
                    // size_t pos = doc_view.find("_id");
                    // while (pos != std::string::npos) {
                    //     if (!isalpha(doc_view[pos - 1])) {
                    //         doc_view.erase(pos, 1);
                    //     }
                    //     pos = doc_view.find("_id", pos + 1);
                    // }

                    all_data_from_db_json_string += doc_view;
                    all_data_from_db_json_string += ",";
                }

                if (all_data_from_db_json_string.back() == ',') {
                    all_data_from_db_json_string.pop_back();
                } // else not required: all_data_from_db_json_string is empty so need to perform any operation
                all_data_from_db_json_string += "]";

                if (!all_data_from_db_json_string.empty()) {
                    return MarketDataJsonToObject::json_to_object(all_data_from_db_json_string, r_root_model_list_obj_out);
                } else {
                    LOG_INFO_IMPL(GetCppAppLogger(), "Databse is empty for collection: {} ", get_root_model_name());
                }
            } catch (const std::exception& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Exception caught in function '{}'. Error: '{}'. "
                                                  "Possible issues: database connection failure, "
                                                  "malformed data in the collection '{}'",
                    __func__, e.what(), get_root_model_name());
            }
            return false;
        }

        bool get_data_from_collection_with_limit(RootModelListType &r_root_model_list_obj_out, const int32_t limit) {
            try {
                std::string all_data_from_db_json_string;
                auto client = m_sp_mongo_db_->get_pool_client();
                mongocxx::database db = (*client)[m_sp_mongo_db_->m_mongo_db_name_];
                auto m_mongo_db_collection_ = db[get_root_model_name()];
                mongocxx::options::find find_options;
                if (limit < 0) {
                    find_options.sort(bsoncxx::builder::basic::make_document(bsoncxx::builder::basic::kvp("_id", -1)));
                }
                find_options.limit(std::abs(limit));
                auto cursor = m_mongo_db_collection_.find({}, find_options);
                all_data_from_db_json_string += "[";
                for (const auto &bson_doc : cursor) {
                    bsoncxx::builder::basic::document new_doc;
                    for (const auto &element: bson_doc) {
                        process_element(element, new_doc);
                    }

                    std::string doc_view = bsoncxx::to_json(new_doc.view());

                    all_data_from_db_json_string += doc_view;
                    all_data_from_db_json_string += ",";
                }

                if (all_data_from_db_json_string.back() == ',') {
                    all_data_from_db_json_string.pop_back();
                } // else not required: all_data_from_db_json_string is empty so need to perform any operation

                all_data_from_db_json_string += "]";

                if (!all_data_from_db_json_string.empty()) {
                    return MarketDataJsonToObject::json_to_object(all_data_from_db_json_string, r_root_model_list_obj_out);
                }
            } catch (const std::exception& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(),
                    "Exception caught in function '{}'. Error: '{}'. Possible issues: database connection failure, "
                    "invalid limit value '{}', malformed data in the collection '{}'",
                    __func__, e.what(), limit, get_root_model_name());
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
                LOG_ERROR_IMPL(GetCppAppLogger(), "Bulk update failed in function '{}'. Collection: '{}', Document "
                                                  "IDs count: {}, BSON documents count: {}.",
                                                  __func__, get_root_model_name(), kr_model_doc_ids.size(),
                                                  kr_bson_doc_list.size());
                return false;
            }
        }

        bool get_data_by_id_from_collection([[maybe_unused]] RootModelType &r_root_model_obj_out, const int32_t &kr_root_model_doc_id) {
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
                    return MarketDataJsonToObject::json_to_object(new_bson_doc, r_root_model_obj_out);
                }
            } catch (const std::exception& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Exception caught in function '{}'. Error: '{}'. Collection: '{}', "
                                                  "Document ID: '{}'.", __func__, e.what(),
                                                  get_root_model_name(), kr_root_model_doc_id);
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
            return result->deleted_count() > 0;
        }

        size_t get_md_key_to_db_id_size() const {
            return m_root_model_key_to_db_id.size();
        }

        int32_t get_max_id_from_collection() {
            int32_t max_id = 0;
            try {
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
            } catch (const std::exception& e) {
                LOG_ERROR_IMPL(GetCppAppLogger(), "Error fetching max ID from collection: {};;; error: {}",
                    get_root_model_name(), e.what());
            }
            return max_id;
        }

        std::unordered_map<std::string, int32_t> m_root_model_key_to_db_id;

    protected:
        template <typename ProtoModelType>
        auto get_db_id_from_key(const std::string &kr_key, [[maybe_unused]] const ProtoModelType &kr_proto_model_obj){
            auto found = m_root_model_key_to_db_id.find(kr_key);
            if (found == m_root_model_key_to_db_id.end()) {
                const std::string error = "Error!" + get_root_model_name() +
                        "key not found in m_root_model_key_to_db_id map;;; map: " + KeyToDbIdAsString();
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

        std::string get_root_model_name() const {
            auto meta_data = root_model_type_.get_name();
            return meta_data;
        }

        static void update_id_in_document(bsoncxx::builder::basic::document &r_bson_doc, const int32_t new_generated_id) {
            r_bson_doc.append(kvp("_id", new_generated_id));
        }

    public:
        int32_t get_next_insert_id() {
            return ++m_max_id_;
        }
    protected:
        std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
        RootModelType root_model_type_;
        static inline int32_t c_cur_unused_max_id_ = 1;
        int32_t m_max_id_;
    };


}
