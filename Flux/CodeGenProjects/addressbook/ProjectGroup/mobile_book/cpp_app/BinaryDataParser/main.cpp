#include <filesystem>
#include <format>

#include "binary_file_reader.h"
#include "../include/md_container.h"
#include "../include/md_utility_functions.h"
#include "../include/shm_symbol_cache.h"

int main(int argc, char *argv[]){

    if (argc != 5) {
        std::cerr << "Usage: " << argv[0] << "<input output file dir> <input file name> <output file name> <market depth level>  " << std::endl;
        return 1;
    }

    if (!std::filesystem::exists(argv[1])) {
        auto err = std::format("Directory '{}' does not exist", argv[1]);
        throw std::runtime_error(err.c_str());
    }

    auto input_file_name = std::filesystem::path(argv[1]) / argv[2];
    if (!std::filesystem::exists(input_file_name)) {
        auto err = std::format("File '{}' does not exist", std::string(input_file_name));
        throw std::runtime_error(err.c_str());
    }

    auto output_file_name = std::filesystem::path(argv[1]) / argv[3];
    std::ofstream output_file_stream(std::string(output_file_name), std::ios::out);

    auto depth_level = stoi(argv[4]);

    switch (depth_level)
    {
        case 1:
            {
                BinaryFileReader<ShmSymbolCache<1>> binary_file_reader(input_file_name);
                std::vector<ShmSymbolCache<1>> shm_symbol_cache;

                binary_file_reader.read(shm_symbol_cache);

                std::vector<char> buffer;
                for (const auto& symbol_cache : shm_symbol_cache) {
                    mobile_book_handler::format_data(symbol_cache.m_leg_1_data_shm_cache_, buffer);
                    output_file_stream << std::string_view(buffer);
                    buffer.clear();
                    mobile_book_handler::format_data(symbol_cache.m_leg_2_data_shm_cache_, buffer);
                    output_file_stream << std::string_view(buffer);
                    buffer.clear();
                    output_file_stream << std::endl;
                }
                break;
            }
        case 5:
            {
                BinaryFileReader<ShmSymbolCache<5>> binary_file_reader(input_file_name);
                std::vector<ShmSymbolCache<5>> shm_symbol_cache;

                binary_file_reader.read(shm_symbol_cache);

                std::vector<char> buffer;
                for (const auto& symbol_cache : shm_symbol_cache) {
                    mobile_book_handler::format_data(symbol_cache.m_leg_1_data_shm_cache_, buffer);
                    output_file_stream << std::string_view(buffer);
                    buffer.clear();
                    mobile_book_handler::format_data(symbol_cache.m_leg_2_data_shm_cache_, buffer);
                    output_file_stream << std::string_view(buffer);
                    buffer.clear();
                    output_file_stream << std::endl;
                }
                break;
            }
        case 10:
            {
                BinaryFileReader<ShmSymbolCache<10>> binary_file_reader(input_file_name);
                std::vector<ShmSymbolCache<10>> shm_symbol_cache;

                binary_file_reader.read(shm_symbol_cache);

                std::vector<char> buffer;
                for (const auto& symbol_cache : shm_symbol_cache) {
                    mobile_book_handler::format_data(symbol_cache.m_leg_1_data_shm_cache_, buffer);
                    output_file_stream << std::string_view(buffer);
                    buffer.clear();
                    mobile_book_handler::format_data(symbol_cache.m_leg_2_data_shm_cache_, buffer);
                    output_file_stream << std::string_view(buffer);
                    buffer.clear();
                    output_file_stream << std::endl;
                }
                break;
            }
        case 15:
            {
                BinaryFileReader<ShmSymbolCache<15>> binary_file_reader(input_file_name);
                std::vector<ShmSymbolCache<15>> shm_symbol_cache;

                binary_file_reader.read(shm_symbol_cache);

                std::vector<char> buffer;
                for (const auto& symbol_cache : shm_symbol_cache) {
                    mobile_book_handler::format_data(symbol_cache.m_leg_1_data_shm_cache_, buffer);
                    output_file_stream << std::string_view(buffer);
                    buffer.clear();
                    mobile_book_handler::format_data(symbol_cache.m_leg_2_data_shm_cache_, buffer);
                    output_file_stream << std::string_view(buffer);
                    buffer.clear();
                    output_file_stream << std::endl;
                }
                break;
            }
        case 20:
            {
                BinaryFileReader<ShmSymbolCache<20>> binary_file_reader(input_file_name);
                std::vector<ShmSymbolCache<20>> shm_symbol_cache;

                binary_file_reader.read(shm_symbol_cache);

                std::vector<char> buffer;
                for (const auto& symbol_cache : shm_symbol_cache) {
                    mobile_book_handler::format_data(symbol_cache.m_leg_1_data_shm_cache_, buffer);
                    output_file_stream << std::string_view(buffer);
                    buffer.clear();
                    mobile_book_handler::format_data(symbol_cache.m_leg_2_data_shm_cache_, buffer);
                    output_file_stream << std::string_view(buffer);
                    buffer.clear();
                    output_file_stream << std::endl;
                }
                break;
            }
    }

    return 0;
}
