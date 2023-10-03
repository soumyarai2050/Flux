#pragma once

#include "random"
#include "string"

class RandomDataGen {
public:
    RandomDataGen() : mt(std::random_device{}()), double_distribution(1, 100.0), int64_distribution(1, 100),
                      string_distribution(0, static_cast<int>(characters.length()) - 1) {
    }

    const std::string get_random_string() {
        std::string randomString;
        randomString.reserve(8);
        for (int i = 0; i < 8; ++i) {
            randomString += characters[string_distribution(mt)];
        }
        return randomString;
    }

    float get_random_float() {
        return float(double_distribution(mt));
    }

    double get_random_double() {
        return double_distribution(mt);
    }

    static int32_t get_random_int32() {
        return int32_value++;
    }

    int64_t get_random_int64() {
        return int64_distribution(mt);
    }

    bool get_random_bool() {
        return bool_distribution(mt) == 1;
    }

protected:
    std::mt19937 mt;  // for random data generation

    std::uniform_real_distribution<double> double_distribution;
    static inline int32_t int32_value = 1;
    std::uniform_int_distribution<int64_t> int64_distribution;

    const std::string characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    std::uniform_int_distribution<int> string_distribution;
    std::uniform_int_distribution<int> bool_distribution{0, 1};

};
