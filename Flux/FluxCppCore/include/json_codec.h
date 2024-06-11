#pragma once

#include <boost/json.hpp>
#include <google/protobuf/util/json_util.h>
#include <absl/status/status.h>

#include "quill/Quill.h"
#include "string_util.h"
#include "logger.h"

namespace FluxCppCore {

    class JsonCodecOptions {
    protected:
        static inline void
        encode_options(google::protobuf::util::JsonPrintOptions &options, const bool whitespace = false) {
            options.add_whitespace = whitespace;
            options.always_print_primitive_fields = whitespace;
            options.preserve_proto_field_names = true;
        }

        static inline void decode_options(google::protobuf::util::JsonParseOptions &options) {
            options.ignore_unknown_fields = true;
        }

        // static inline quill::Logger *c_p_logger_{GetLogger()};
    };

    template<typename RootModelType>
    class RootModelJsonCodec : public JsonCodecOptions {
        // using JsonCodecOptions::c_p_logger_;
    protected:
        static inline void modify_json(std::string &r_json_str) {
            try {
                boost::json::value jv = boost::json::parse(r_json_str);
                boost::json::object& obj = jv.as_object();
                if (obj["side"].is_string()) {
                    std::string side = std::string(obj["side"].as_string().c_str());
                    if (side == "BID") {
                        obj["side"] = 2;
                    } else if (side == "ASK") {
                        obj["side"] = 3;
                    }
                } else {
                    LOG_ERROR(GetLogger(), "Error: 'side' field is not a string in JSON. JSON: {}", r_json_str);
                }
                r_json_str = boost::json::serialize(jv);
            } catch (const std::invalid_argument& e) {
                LOG_ERROR(GetLogger(), "Invalid argument encountered: {}, JSON: {}", e.what(), r_json_str);
            } catch (const boost::json::system_error& e) {
                LOG_ERROR(GetLogger(), "Parse error encountered: {}, JSON: {}", e.what(), r_json_str);
            }
        }

    public:

        [[nodiscard]] static inline bool decode_model(RootModelType &r_model_obj, std::string &kr_json) {
            google::protobuf::util::JsonParseOptions options;
            decode_options(options);
            StringUtil string_util;
            std::string msg_name = string_util.camel_to_snake(RootModelType::GetDescriptor()->name());
            if (msg_name == "market_depth") {
                modify_json(kr_json);
            }
            absl::Status status = google::protobuf::util::JsonStringToMessage(kr_json, &r_model_obj,
                                                                                                options);
            if (status.code() == absl::StatusCode::kOk) {
                return true;
            } else {
                LOG_ERROR(GetLogger(), "Failed Decoding {};;; error: {};;; json: {}",
                          RootModelType::GetDescriptor()->name(), status.message(), kr_json);
                return false;
            }
        }

        [[nodiscard]] static inline bool
        encode_model(const RootModelType &kr_model_obj, std::string &r_json_out, const bool whitespace = false) {
            google::protobuf::util::JsonPrintOptions options;
            encode_options(options, whitespace);
            absl::Status status = google::protobuf::util::MessageToJsonString(kr_model_obj,
                                                                                                &r_json_out,
                                                                                                options);
            if (status.code() == absl::StatusCode::kOk)
                return true;
            else {
                LOG_ERROR(GetLogger(), "Failed Encoding {};;; error: {};;; {}: {}",
                          RootModelType::GetDescriptor()->name(), status.message(),
                          RootModelType::GetDescriptor()->name(), kr_model_obj.DebugString());
                return false;
            }
        }
    };

    template<typename RootModelListType>
    class RootModelListJsonCodec : public JsonCodecOptions {
        // using JsonCodecOptions::c_p_logger_;
    protected:

        static inline void modify_json(std::string &r_json_str) {
            // Parse the JSON string into a JSON object
            boost::json::value jv = boost::json::parse(r_json_str);
            boost::json::object& obj = jv.as_object();

            // Access the "market_depth" array
            boost::json::array& market_depth = obj["market_depth"].as_array();

            // Iterate over the objects in the array
            for (auto& item : market_depth) {
                try {
                    boost::json::object& item_obj = item.as_object();

                    // Replace "BID" with 1 and "ASK" with 2 in the "side" field
                    if (item_obj["side"].as_string() == "BID") {
                        item_obj["side"] = 2;
                    } else if (item_obj["side"].as_string() == "ASK") {
                        item_obj["side"] = 3;
                    } else {
                        LOG_ERROR(GetLogger(), "Error: 'side' field is not a string in JSON. JSON: {}", r_json_str);
                    }
                    // Serialize the JSON object back into a string
                    r_json_str = boost::json::serialize(jv);
                } catch (const std::invalid_argument& e) {
                    LOG_ERROR(GetLogger(), "Invalid argument encountered: {}, JSON: {}", e.what(), r_json_str);
                } catch (const boost::json::system_error& e) {
                    LOG_ERROR(GetLogger(), "Parse error encountered: {}, JSON: {}", e.what(), r_json_str);
                }
            }
        }

    public:

        [[nodiscard]] static inline bool
        encode_model_list(const RootModelListType &kr_model_list_obj, std::string &r_list_json_out,
                          const bool whitespace = false) {
            google::protobuf::util::JsonPrintOptions options;
            encode_options(options, whitespace);
            absl::Status status = google::protobuf::util::MessageToJsonString(kr_model_list_obj,
                                                                                                &r_list_json_out,
                                                                                                options);
            if (status.code() == absl::StatusCode::kOk) {
                size_t pos = r_list_json_out.find(":[{");
                if (pos != std::string::npos) {
                    //refer to example_comments.txt for before substr and after substr
                    r_list_json_out = r_list_json_out.substr(pos + 1, r_list_json_out.size() - pos - 2);
                    return true;
                } // else not required: when we try to encode empty string we'll not find `:[{` as substr
                return true;
            } else {
                LOG_ERROR(GetLogger(), "Failed Encoding {};;; error: {};;; {}: {}",
                          RootModelListType::GetDescriptor()->name(), status.message(),
                          RootModelListType::GetDescriptor()->name(), kr_model_list_obj.DebugString());
                return false;
            }
        }

        // ideally dash_list_json should have been a const - but we intend to reuse the top_of_book_list_json to avoid creating new string
        [[nodiscard]] static inline bool
        decode_model_list(RootModelListType &r_model_list_obj_out, std::string &r_list_json) {
            google::protobuf::util::JsonParseOptions options;
            StringUtil stringUtil;
            decode_options(options);
            const std::string target = "_list";
            std::string msg_name = stringUtil.camel_to_snake(RootModelListType::GetDescriptor()->name());
            size_t pos = msg_name.find(target);
            if (pos != std::string::npos) {
                msg_name.erase(pos, target.length());
            }
            pos = r_list_json.find(":[");
            if (pos == std::string::npos && r_list_json.back() != ']')
                r_list_json = "[" + r_list_json + "]";
            r_list_json = "{\"" + msg_name + "\":" + r_list_json + '}';

            if (msg_name == "market_depth")
                modify_json(r_list_json);

            absl::Status status = google::protobuf::util::JsonStringToMessage(r_list_json,
                                                                              &r_model_list_obj_out, options);
            if (status.code() == absl::StatusCode::kOk) {
                return true;
            } else {
                LOG_ERROR(GetLogger(), "Failed Decoding {};;; error: {};;; list_json: {}",
                          RootModelListType::GetDescriptor()->name(), status.message(), r_list_json);
                return false;
            }

        }
    };
}