#pragma once

#include <unordered_map>
#include <string>
#include <any>

namespace market_data_handler {

    class GenericCache {

    public:
        template <typename T>
        void insert(const std::string& key, const T& value) {
            data_[key] = std::make_shared<std::any>(value);
        }

        template <typename T>
        bool retrieve(const std::string& key, T& value) {
            auto it = data_.find(key);
            if (it != data_.end()) {
                value = std::any_cast<T>(*it->second); // Dereference the shared_ptr when casting
                return true;
            }
            return false;
        }

        void remove(const std::string& key) {
            data_.erase(key);
        }

        bool exists(const std::string& key) {
            return data_.find(key) != data_.end();
        }

    protected:
        std::unordered_map<std::string, std::shared_ptr<std::any>> data_;
    };

}