#pragma once

#include <google/protobuf/util/json_util.h>

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

        static inline quill::Logger *logger_;
    };

    template<typename RootModelType>
    class RootModelJsonCodec : public JsonCodecOptions {
        using JsonCodecOptions::logger_;
    public:
        [[nodiscard]] static inline bool decode_model(RootModelType &model_obj, const std::string &json) {
            google::protobuf::util::JsonParseOptions options;
            decode_options(options);
            google::protobuf::util::Status status = google::protobuf::util::JsonStringToMessage(json, &model_obj,
                                                                                                options);
            if (status.code() == google::protobuf::util::StatusCode::kOk) {
                return true;
            } else {
                LOG_ERROR(logger_, "Failed Decoding {}, error: {} json: {}", RootModelType::GetDescriptor()->full_name(),
                          status.message().ToString(), json);
                return false;
            }
        }

        [[nodiscard]] static inline bool
        encode_model(const RootModelType &model_obj, std::string &json_out, const bool whitespace = false) {
            google::protobuf::util::JsonPrintOptions options;
            encode_options(options, whitespace);
            google::protobuf::util::Status status = google::protobuf::util::MessageToJsonString(model_obj,
                                                                                                &json_out,
                                                                                                options);
            if (status.code() == google::protobuf::util::StatusCode::kOk)
                return true;
            else {
                LOG_ERROR(logger_, "Failed Encoding {}, error: {} {}: {}", RootModelType::GetDescriptor()->full_name(),
                          status.message().ToString(), RootModelType::GetDescriptor()->full_name(),
                          model_obj.DebugString());
                return false;
            }
        }
    };

    template<typename RootModelListType>
    class RootModelListJsonCodec : public JsonCodecOptions {
        using JsonCodecOptions::logger_;
    public:

        [[nodiscard]] static inline bool
        encode_model_list(const RootModelListType &model_list_obj, std::string &list_json_out,
                          const bool whitespace = false) {
            google::protobuf::util::JsonPrintOptions options;
            encode_options(options, whitespace);
            google::protobuf::util::Status status = google::protobuf::util::MessageToJsonString(model_list_obj,
                                                                                                &list_json_out,
                                                                                                options);
            if (status.code() == google::protobuf::util::StatusCode::kOk) {
                size_t pos = list_json_out.find(":[{");
                if (pos != std::string::npos) {
                    //refer to example_comments.txt for before substr and after substr
                    list_json_out = list_json_out.substr(pos + 1, list_json_out.size() - pos - 2);
                    return true;
                } // else not required: when we try to encode empty string we'll not find `:[{` as substr
                return true;
            } else {
                LOG_ERROR(logger_, "Failed Encoding {}, error: {} {}: {}", RootModelListType::GetDescriptor()->full_name(),
                          status.message().ToString(), RootModelListType::GetDescriptor()->full_name(),
                          model_list_obj.DebugString());
                return false;
            }
        }

        // ideally dash_list_json should have been a const - but we intend to reuse the top_of_book_list_json to avoid creating new string
        [[nodiscard]] static inline bool
        decode_model_list(RootModelListType &model_list_obj_out, std::string &list_json) {
            google::protobuf::util::JsonParseOptions options;
            StringUtil stringUtil;
            decode_options(options);
            const std::string target = "_list";
            std::string msg_name = stringUtil.camel_to_snake(RootModelListType::GetDescriptor()->name());
            size_t pos = msg_name.find(target);
            if (pos != std::string::npos) {
                msg_name.erase(pos, target.length());
            }
            pos = list_json.find(":[");
            if (pos == std::string::npos && list_json.back() != ']')
                list_json = "[" + list_json + "]";
            list_json = "{\"" + msg_name + "\":" + list_json + '}';
            google::protobuf::util::Status status = google::protobuf::util::JsonStringToMessage(list_json,
                                                                                                &model_list_obj_out,
                                                                                                options);
            if (status.code() == google::protobuf::util::StatusCode::kOk) {
                return true;
            } else {
                LOG_ERROR(logger_, "Failed Decoding {}, error: {} list_json: {}", RootModelListType::GetDescriptor()->name(),
                          status.message().ToString(), list_json);
                return false;
            }

        }
    };
}