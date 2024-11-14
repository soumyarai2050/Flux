#include <filesystem>
#include <format>

#include "../include/binary_file_reader.h"
#include "../include/md_container.h"
#include "../include/md_utility_functions.h"
#include "../include/shm_symbol_cache.h"

int main(int argc, char *argv[]){

    if (argc != 4) {
        std::cerr << "Usage: " << argv[0] << "<input output file dir> <input file name> <output file name>" << std::endl;
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

    BinaryFileReader<ShmSymbolCache> binary_file_reader(input_file_name);
    std::vector<ShmSymbolCache> shm_symbol_cache;

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

    return 0;
}
