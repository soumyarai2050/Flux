#pragma once

#include <boost/beast.hpp>
#include <boost/asio/ip/tcp.hpp>

#include "TemplateUtils.h"
#include "json_codec.h"
#include "project_includes.h"

namespace FluxCppCore {

    class BaseWebClient {
    public:
        BaseWebClient(const std::string &kr_host, const std::string &kr_port) : km_host_(kr_host), km_port_(kr_port) {
            static_init(km_host_, km_port_);
        }

    protected:
        const std::string km_host_;
        const std::string km_port_;
        static boost::asio::io_context c_io_context_;
        static boost::asio::ip::tcp::resolver c_resolver_;
        static boost::asio::ip::tcp::socket c_socket_;
        static boost::asio::ip::tcp::resolver::results_type c_result_;
        static inline bool c_static_members_initialized_ = false;
        static std::mutex c_market_data_web_client_mutex;
        quill::Logger* m_p_logger_ = quill::get_logger();

        static void static_init(const std::string &kr_host, const std::string &kr_port) {
            const std::lock_guard<std::mutex> lock(c_market_data_web_client_mutex);
            if (!c_static_members_initialized_) {
                if (!c_io_context_.stopped()) {
                    // Initialize socket and connect using the resolved results
                    c_result_ = c_resolver_.resolve(kr_host, kr_port);
                    c_socket_ = boost::asio::ip::tcp::socket(c_io_context_);
                    boost::asio::connect(c_socket_, c_result_);
                }
                c_static_members_initialized_ = true;
            }
        }

        [[nodiscard]] bool send_http_request(const boost::beast::http::verb &kr_method, const std::string_view url,
        const std::string_view request_json, std::string &response_json_out) const {
            // Construct an HTTP request object with the specified HTTP method, URL, and version
            boost::beast::http::request<boost::beast::http::string_body> request{kr_method, url, 11};
            // Set the host and user agent fields in the HTTP request headers
            request.set(boost::beast::http::field::host, km_host_);
            request.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);

            if (!request_json.empty()) {
                request.set(boost::beast::http::field::content_type, "application/json");
                request.body() = request_json;
                request.set(boost::beast::http::field::content_length, std::to_string(request_json.size()));
                request.prepare_payload();
            } // else not required: If there's request JSON data, set the content type, body, and content length in the request headers

            boost::asio::ip::tcp::socket synchronous_socket(c_socket_.get_executor());
            boost::asio::connect(synchronous_socket, c_result_);
            boost::beast::http::write(synchronous_socket, request);

            boost::beast::error_code error_code_obj;
            boost::beast::flat_buffer buffer;
            boost::beast::http::response_parser<boost::beast::http::dynamic_body> response_parser_obj;
            response_parser_obj.body_limit(boost::none);
            boost::beast::http::read(synchronous_socket, buffer, response_parser_obj, error_code_obj);

            if (error_code_obj) {
                std::cerr << "An error occurred: " << error_code_obj.message() << std::endl;
            }
            response_json_out = boost::beast::buffers_to_string(response_parser_obj.get().body().data());
            return !response_json_out.empty();
        }

        [[nodiscard]] bool send_get_request(const std::string_view url, std::string &r_response_json_out) const {
            return send_http_request(boost::beast::http::verb::get, url, "", r_response_json_out);
        }

        [[nodiscard]] bool send_get_request(std::string_view get_url, const int32_t &kr_id, std::string &r_response_json_out) const {
            return send_http_request(boost::beast::http::verb::get, std::string (get_url) + "/" +
            std::to_string(kr_id), "", r_response_json_out);
        }

        [[nodiscard]] bool send_post_request(std::string_view post_url, std::string_view post_json, std::string
        &r_response_json_out) const {
            return send_http_request(boost::beast::http::verb::post, post_url, post_json, r_response_json_out);
        }

        [[nodiscard]] bool send_patch_request(std::string_view patch_url, std::string_view patch_json,
        std::string &r_response_json_out) const {
            return send_http_request(boost::beast::http::verb::patch, patch_url, patch_json, r_response_json_out);
        }

        [[nodiscard]] bool send_put_request(std::string_view put_url, std::string_view put_json,
        std::string &r_response_json_out) const {
            return send_http_request(boost::beast::http::verb::put, put_url, put_json, r_response_json_out);
        }

        [[nodiscard]] bool send_delete_request(std::string_view delete_url, const int32_t &kr_id, std::string
        &r_response_json_out) const {
            return send_http_request(boost::beast::http::verb::delete_, std::string (delete_url) + "/" +
            std::to_string(kr_id), "", r_response_json_out);
        }
    };


    template <typename RootModelType,
            StringLiteral create_client_url,
            StringLiteral get_client_url,
            StringLiteral get_max_id_client_url,
            StringLiteral put_client_url,
            StringLiteral patch_client_url,
            StringLiteral delete_client_url>
    class RootModelWebClient : public BaseWebClient {
    public:
        RootModelWebClient(const std::string &kr_host, const std::string &kr_port) : BaseWebClient(kr_host, kr_port) {}

        [[nodiscard]] auto get_max_id_client() const {
            std::string json_out;
            int32_t new_max_id = 0;
            std::string_view get_max_id_client_url_view = get_max_id_client_url.value;
            bool status = send_get_request(get_max_id_client_url_view, json_out);
            if (status) {
                // Find the starting position of the `max_id_val` within the JSON string and calculate the position
                // where the value associated with it begins. We add the length of `max_id_val_key` and 2 to skip dual-quote
                // and the colon character in the string.
                size_t start_pos = json_out.find(max_id_val_key) +
                        max_id_val_key.length() + 2;
                size_t end_pos = json_out.find_first_of("}", start_pos);
                if (start_pos != std::string::npos && end_pos != std::string::npos) {
                    std::string max_id_str = json_out.substr(start_pos, end_pos - start_pos);
                    try {
                        new_max_id = std::stoi(max_id_str);
                    } catch (const std::exception& e) {
                        LOG_ERROR(m_p_logger_, "Error parsing {} max_id_val: {}", RootModelType::GetDescriptor()->name(), e.what());
                    }
                }
                return new_max_id;
            } else {
                LOG_ERROR(m_p_logger_, "Error while performing get {} max_id_val request: {}, url: {}",
                          RootModelType::GetDescriptor()->name(), json_out, get_max_id_client_url_view);
                return new_max_id;
            }
        }

        [[nodiscard]] bool get_client(RootModelType &r_obj_out, const int32_t &kr_id) const {
            bool status = false;
            std::string json_out;
            std::string_view get_client_url_view = get_client_url.value;
            status = send_get_request(get_client_url_view, kr_id, json_out);
            if (status) {
                std::string modified_json;
                for (int i = 0; i < json_out.size(); ++i) {
                    if (json_out[i] == '_' && (i + 1 < json_out.size()) && json_out[i + 1] == 'i' && json_out[i + 2]
                    == 'd' && ( i > 0 && !std::isalnum(json_out[i - 1]))) {
                        // Skip the underscore if `_id` is detected
                        // Do nothing, and let the loop increment i automatically
                    } else {
                        // Copy the character to the modified json
                        modified_json += json_out[i];
                    }
                }

                status =  m_codec.decode_model(r_obj_out, modified_json);
                return status;
            } else {
                return status;
            }
        }

        [[nodiscard]] bool create_client (RootModelType &r_obj_in_n_out) {
            std::string json;
            bool status = m_codec.encode_model(r_obj_in_n_out, json, true);
            if (status) {
                std::string json_out;
                std::string_view create_client_url_view = create_client_url.value;
                status = send_post_request(create_client_url_view, json, json_out);
                if (status) {
                    std::string modified_json;
                    for (int i = 0; i < json_out.size(); ++i) {
                        if (json_out[i] == '_' && (i + 1 < json_out.size()) && json_out[i + 1] == 'i' &&
                        json_out[i + 2] == 'd' && ( i > 0 && !std::isalnum(json_out[i - 1]))) {
                            // Skip the underscore if `_id` is detected
                            // Do nothing, and let the loop increment i automatically
                        } else {
                            // Copy the character to the modified json
                            modified_json += json_out[i];
                        }
                    }
                    r_obj_in_n_out.Clear();
                    status =  m_codec.decode_model(r_obj_in_n_out, modified_json);
                    return status;
                } else {
                    LOG_ERROR(m_p_logger_, "Error while creating {}: {} url: {}", RootModelType::GetDescriptor()->name(),
                              json, create_client_url_view);
                    return false;
                }
            } else {
                LOG_ERROR(m_p_logger_, "Error while encoding {}: {}", RootModelType::GetDescriptor()->name(),
                          r_obj_in_n_out.DebugString());
                return false;
            }
            return status;
        }

        [[nodiscard]] bool patch_client (RootModelType &r_obj_in_n_out) const {
            std::string json;
            bool status = m_codec.encode_model(r_obj_in_n_out, json);
            if (status) {
                size_t pos = json.find("id");
                while (pos != std::string::npos) {
                    // Check if there's no underscore before `id`
                    if (pos == 0 || json[pos - 1] != '_' && (!std::isalpha(json[pos - 1]))) {
                        // Insert the underscore before `id`
                        json.insert(pos, "_");
                        // Move the search position to the end of the inserted underscore
                        pos += 1;
                    }
                    // Find the next occurrence of `id`
                    pos = json.find("id", pos + 1);
                }

                std::string json_out;
                std::string_view patch_client_url_view = patch_client_url.value;
                status = send_patch_request(patch_client_url_view, json, json_out);
                if (status) {
                    std::string modified_json;
                    for (int i = 0; i < json_out.size(); ++i) {
                        if (json_out[i] == '_' && (i + 1 < json_out.size()) && json_out[i + 1] == 'i' &&
                        json_out[i + 2] == 'd' && ( i > 0 && !std::isalnum(json_out[i - 1]))) {
                            // Skip the underscore if `_id` is detected
                            // Do nothing, and let the loop increment i automatically
                        } else {
                            // Copy the character to the modified json
                            modified_json += json_out[i];
                        }
                    }
                    r_obj_in_n_out.Clear();
                    status =  m_codec.decode_model(r_obj_in_n_out, modified_json);
                    return status;
                } else {
                    LOG_ERROR(m_p_logger_, "Error while patch {}: {} url: {}", RootModelType::GetDescriptor()->name(),
                    json, patch_client_url_view);
                    return false;
                }
            } else {
                LOG_ERROR(m_p_logger_, "Error while encoding {}: {}", RootModelType::GetDescriptor()->name(),
                          r_obj_in_n_out.DebugString());
                return false;
            }
            return status;
        }

        [[nodiscard]] bool put_client (RootModelType &r_obj_in_n_out) const {
            std::string json;
            bool status = m_codec.encode_model(r_obj_in_n_out, json, true);
            if (status) {
                size_t pos = json.find("id");
                while (pos != std::string::npos) {
                    // Check if there's no underscore before `id`
                    if (pos == 0 || json[pos - 1] != '_' && (!std::isalpha(json[pos - 1]))) {
                        // Insert the underscore before `id`
                        json.insert(pos, "_");
                        // Move the search position to the end of the inserted underscore
                        pos += 1;
                    }
                    // Find the next occurrence of `id`
                    pos = json.find("id", pos + 1);
                }
                std::string json_out;
                std::string_view put_client_url_view = put_client_url.value;
                status = send_put_request(put_client_url_view, json, json_out);

                if (status) {
                    std::string modified_json;
                    for (int i = 0; i < json_out.size(); ++i) {
                        if (json_out[i] == '_' && (i + 1 < json_out.size()) && json_out[i + 1] == 'i'
                        && json_out[i + 2] == 'd' && ( i > 0 && !std::isalnum(json_out[i - 1]))) {
                            // Skip the underscore if `_id` is detected
                            // Do nothing, and let the loop increment i automatically
                        } else {
                            // Copy the character to the modified json
                            modified_json += json_out[i];
                        }
                    }
                    status =  m_codec.decode_model(r_obj_in_n_out, modified_json);
                } else {
                    LOG_ERROR(m_p_logger_, "Error while put {}: {} url: {}", RootModelType::GetDescriptor()->name(),
                              json, put_client_url_view);
                    return false;
                }
            } else {
                LOG_ERROR(m_p_logger_, "Error while encoding {}: {}", RootModelType::GetDescriptor()->name(),
                          r_obj_in_n_out.DebugString());
                return false;
            }
            return status;
        }

        [[nodiscard]] std::string delete_client (const int32_t &kr_id) const {
            std::string delete_response_json;
            std::string_view delete_client_url_view = delete_client_url.value;
            bool status = send_delete_request(delete_client_url_view, kr_id, delete_response_json);
            if (status) {
                return delete_response_json;
            } else {
                LOG_ERROR(m_p_logger_, "Error while delete {}: {}, id: {}, url: {}", RootModelType::GetDescriptor()->name(),
                delete_response_json, kr_id, delete_client_url_view);
                return delete_response_json;
            }
        }

    protected:
        quill::Logger* m_p_logger_ = quill::get_logger();
        RootModelJsonCodec<RootModelType> m_codec;
    };

    template <typename RootModelListType,
            StringLiteral create_client_url,
            StringLiteral get_client_url,
            StringLiteral get_max_id_client_url,
            StringLiteral put_client_url,
            StringLiteral patch_client_url,
            StringLiteral delete_client_url>
    class RootModelListWebClient : public BaseWebClient {
    public:
        RootModelListWebClient(const std::string &kr_host, const std::string &kr_port) : BaseWebClient(kr_host, kr_port) {}

        [[nodiscard]] auto get_max_id_client() const {
            std::string json_out;
            int32_t new_max_id = 0;
            std::string_view get_max_id_client_url_view = get_max_id_client_url.value;
            bool status = send_get_request(get_max_id_client_url_view, json_out);
            if (status) {
                // Find the starting position of the `max_id_val` within the JSON string and calculate the position
                // where the value associated with it begins. We add the length of `max_id_val_key` and 2 to skip dual-quote
                // and the colon character in the string.
                size_t start_pos = json_out.find(max_id_val_key) +
                                   max_id_val_key.length() + 2;
                size_t end_pos = json_out.find_first_of("}", start_pos);
                if (start_pos != std::string::npos && end_pos != std::string::npos) {
                    std::string max_id_str = json_out.substr(start_pos, end_pos - start_pos);
                    try {
                        new_max_id = std::stoi(max_id_str);
                    } catch (const std::exception& e) {
                        LOG_ERROR(m_p_logger_, "Error parsing {} max_id_val: {}",
                                  RootModelListType::GetDescriptor()->name(), e.what());
                    }
                }
                return new_max_id;
            } else {
                LOG_ERROR(m_p_logger_, "Error while performing get {} max_id_val request: {}, url: {}",
                          RootModelListType::GetDescriptor()->name(), json_out, get_max_id_client_url_view);
                return new_max_id;
            }
        }

        [[nodiscard]] bool get_client(RootModelListType &r_obj_out, const int32_t &kr_id) const {
            bool status = false;
            std::string json_out;
            std::string_view get_client_url_view = get_client_url.value;
            status = send_get_request(get_client_url_view, kr_id, json_out);
            if (status) {
                std::string modified_json;
                for (int i = 0; i < json_out.size(); ++i) {
                    if (json_out[i] == '_' && (i + 1 < json_out.size()) && json_out[i + 1] == 'i' &&
                    json_out[i + 2] == 'd' && ( i > 0 && !std::isalnum(json_out[i - 1]))) {
                        // Skip the underscore if `_id` is detected
                        // Do nothing, and let the loop increment i automatically
                    } else {
                        // Copy the character to the modified json
                        modified_json += json_out[i];
                    }
                }

                status =  m_codec.decode_model_list(r_obj_out, modified_json);
                return status;
            } else {
                return status;
            }
        }

        [[nodiscard]] bool create_client (RootModelListType &r_obj_in_n_out) {
            std::string json;
            bool status = m_codec.encode_model_list(r_obj_in_n_out, json);
            if (status) {
                std::string json_out;
                std::string_view create_client_url_view = create_client_url.value;
                status = send_post_request(create_client_url_view, json, json_out);
                if (status) {
                    std::string modified_json;
                    for (int i = 0; i < json_out.size(); ++i) {
                        if (json_out[i] == '_' && (i + 1 < json_out.size()) && json_out[i + 1] == 'i' &&
                            json_out[i + 2] == 'd' && ( i > 0 && !std::isalnum(json_out[i - 1]))) {
                            // Skip the underscore if `_id` is detected
                            // Do nothing, and let the loop increment i automatically
                        } else {
                            // Copy the character to the modified json
                            modified_json += json_out[i];
                        }
                    }
                    r_obj_in_n_out.Clear();
                    status =  m_codec.decode_model_list(r_obj_in_n_out, modified_json);
                    return status;
                } else {
                    LOG_ERROR(m_p_logger_, "Error while creating {}: {} url: {}", RootModelListType::GetDescriptor()->name(),
                              json, create_client_url_view);
                    return false;
                }
            } else {
                LOG_ERROR(m_p_logger_, "Error while encoding {}: {}", RootModelListType::GetDescriptor()->name(),
                          r_obj_in_n_out.DebugString());
                return false;
            }
            return status;
        }

        [[nodiscard]] bool patch_client (RootModelListType &r_obj_in_n_out) const {
            std::string json;
            bool status = m_codec.encode_model_list(r_obj_in_n_out, json);
            if (status) {
                size_t pos = json.find("id");
                while (pos != std::string::npos) {
                    // Check if there's no underscore before `id`
                    if (pos == 0 || json[pos - 1] != '_' && (!std::isalpha(json[pos - 1]))) {
                        // Insert the underscore before `id`
                        json.insert(pos, "_");
                        // Move the search position to the end of the inserted underscore
                        pos += 1;
                    }
                    // Find the next occurrence of `id`
                    pos = json.find("id", pos + 1);
                }

                std::string json_out;
                std::string_view patch_client_url_view = patch_client_url.value;
                status = send_patch_request(patch_client_url_view, json, json_out);
                if (status) {
                    std::string modified_json;
                    for (int i = 0; i < json_out.size(); ++i) {
                        if (json_out[i] == '_' && (i + 1 < json_out.size()) && json_out[i + 1] == 'i' &&
                            json_out[i + 2] == 'd' && ( i > 0 && !std::isalnum(json_out[i - 1]))) {
                            // Skip the underscore if `_id` is detected
                            // Do nothing, and let the loop increment i automatically
                        } else {
                            // Copy the character to the modified json
                            modified_json += json_out[i];
                        }
                    }
                    r_obj_in_n_out.Clear();
                    status =  m_codec.decode_model_list(r_obj_in_n_out, modified_json);
                    return status;
                } else {
                    LOG_ERROR(m_p_logger_, "Error while patch {}: {} url: {}", RootModelListType::GetDescriptor()->name(),
                              json, patch_client_url_view);
                    return false;
                }
            } else {
                LOG_ERROR(m_p_logger_, "Error while encoding {}: {}", RootModelListType::GetDescriptor()->name(),
                          r_obj_in_n_out.DebugString());
                return false;
            }
            return status;
        }

        [[nodiscard]] bool put_client (RootModelListType &r_obj_in_n_out) const {
            std::string json;
            bool status = m_codec.encode_model_list(r_obj_in_n_out, json);
            if (status) {
                size_t pos = json.find("id");
                while (pos != std::string::npos) {
                    // Check if there's no underscore before `id`
                    if (pos == 0 || json[pos - 1] != '_' && (!std::isalpha(json[pos - 1]))) {
                        // Insert the underscore before `id`
                        json.insert(pos, "_");
                        // Move the search position to the end of the inserted underscore
                        pos += 1;
                    }
                    // Find the next occurrence of `id`
                    pos = json.find("id", pos + 1);
                }
                std::string json_out;
                std::string_view put_client_url_view = put_client_url.value;
                status = send_put_request(put_client_url_view, json, json_out);

                if (status) {
                    std::string modified_json;
                    for (int i = 0; i < json_out.size(); ++i) {
                        if (json_out[i] == '_' && (i + 1 < json_out.size()) && json_out[i + 1] == 'i'
                            && json_out[i + 2] == 'd' && ( i > 0 && !std::isalnum(json_out[i - 1]))) {
                            // Skip the underscore if `_id` is detected
                            // Do nothing, and let the loop increment i automatically
                        } else {
                            // Copy the character to the modified json
                            modified_json += json_out[i];
                        }
                    }
                    status =  m_codec.decode_model_list(r_obj_in_n_out, modified_json);
                } else {
                    LOG_ERROR(m_p_logger_, "Error while put {}: {} url: {}", RootModelListType::GetDescriptor()->name(),
                              json, put_client_url_view);
                    return false;
                }
            } else {
                LOG_ERROR(m_p_logger_, "Error while encoding {}: {}", RootModelListType::GetDescriptor()->name(),
                          r_obj_in_n_out.DebugString());
                return false;
            }
            return status;
        }


    protected:
        quill::Logger* m_p_logger_ = quill::get_logger();
        RootModelListJsonCodec<RootModelListType> m_codec;
    };

}
