#pragma once

#include <google/protobuf/util/json_util.h>
#include <absl/status/status.h>

#include "quill/Quill.h"
#include "string_util.h"

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

        static inline quill::Logger *c_p_logger_;
    };

    template<typename RootModelType>
    class RootModelJsonCodec : public JsonCodecOptions {
        using JsonCodecOptions::c_p_logger_;
    public:
        [[nodiscard]] static inline bool decode_model(RootModelType &r_model_obj, const std::string &kr_json) {
            google::protobuf::util::JsonParseOptions options;
            decode_options(options);
            absl::Status status = google::protobuf::util::JsonStringToMessage(kr_json, &r_model_obj,
                                                                                                options);
            if (status.code() == absl::StatusCode::kOk) {
                return true;
            } else {
                LOG_ERROR(c_p_logger_, "Failed Decoding {};;; error: {};;; json: {}",
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
                LOG_ERROR(c_p_logger_, "Failed Encoding {};;; error: {};;; {}: {}",
                          RootModelType::GetDescriptor()->name(), status.message(),
                          RootModelType::GetDescriptor()->name(), kr_model_obj.DebugString());
                return false;
            }
        }
    };

    template<typename RootModelListType>
    class RootModelListJsonCodec : public JsonCodecOptions {
        using JsonCodecOptions::c_p_logger_;
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
                LOG_ERROR(c_p_logger_, "Failed Encoding {};;; error: {};;; {}: {}",
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
            absl::Status status = google::protobuf::util::JsonStringToMessage(r_list_json,
                                                                              &r_model_list_obj_out, options);
            if (status.code() == absl::StatusCode::kOk) {
                return true;
            } else {
                LOG_ERROR(c_p_logger_, "Failed Decoding {};;; error: {};;; list_json: {}",
                          RootModelListType::GetDescriptor()->name(), status.message(), r_list_json);
                return false;
            }

        }
    };
}