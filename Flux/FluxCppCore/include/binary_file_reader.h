#pragma once

#include <iostream>
#include <fstream>
#include <string>
#include <vector>

template<typename T>
class BinaryFileReader {
public:
    explicit BinaryFileReader(const std::string& file_path)
        : file_path_(file_path), f_ptr_(fopen(file_path_.c_str(), "rb")) {
        if (!f_ptr_) {
            perror("Error opening file for reading");
        }
    }

    ~BinaryFileReader() {
        if (f_ptr_) {
            fclose(f_ptr_);
        }
    }

    void read(std::vector<T>& data_vector) {

        if (!f_ptr_) {
            std::cerr << "File is not open!" << std::endl;
            return;
        }

        T data;
        while (true) {
            // Read a single element from the file
            size_t num_read = fread(&data, sizeof(T), 1, f_ptr_);
            if (num_read != 1) {
                if (feof(f_ptr_)) {
                    break; // End of file reached
                } else {
                    perror("Error reading from file");
                    data_vector.clear(); // Clear any partially read data on error
                    break;
                }
            }
            data_vector.push_back(data); // Add the successfully read data to the vector
        }
    }

protected:
    std::string file_path_;
    FILE* f_ptr_; // File pointer for reading
};
