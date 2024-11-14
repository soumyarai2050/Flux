#pragma once

#include <iostream>
#include <fstream>
#include <string>

class BinaryFileWriter {
public:
    explicit BinaryFileWriter(const std::string& file_path)
        : file_path_(file_path), f_ptr_(fopen(file_path_.c_str(), "ab")) {
        if (!f_ptr_) {
            perror("Error opening file");
        }
    }

    ~BinaryFileWriter() {
        if (f_ptr_) {
            fclose(f_ptr_);
        }
    }

    template<typename T>
    void write(const T& data) {
        if (!f_ptr_) {
            std::cerr << "File is not open!" << std::endl;
            return;
        }

        // Write the data to the file
        size_t num_written = fwrite(&data, sizeof(T), 1, f_ptr_);
        if (num_written != 1) {
            perror("Error writing to file");
        }
    }

protected:
    std::string file_path_;
    FILE* f_ptr_; // File pointer for writing
};
