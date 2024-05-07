cmake_minimum_required(VERSION 3.28)
project(experiments)

set(CMAKE_CXX_STANDARD 17)

# Include Python headers
include_directories(/usr/include/python3.12/)

# Generate executable
add_executable(experiments main.cpp)

# Generate shared library
add_library(experiments_lib SHARED main.cpp)

# Link Python library to both executable and shared library
target_link_libraries(experiments /lib/x86_64-linux-gnu/libpython3.12.so)
target_link_libraries(experiments_lib /lib/x86_64-linux-gnu/libpython3.12.so)

# Set the output directory for the shared library
set_target_properties(experiments_lib PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)
