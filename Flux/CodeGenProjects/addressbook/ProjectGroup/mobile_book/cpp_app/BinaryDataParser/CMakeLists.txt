cmake_minimum_required(VERSION 3.22)
set(CMAKE_CXX_STANDARD 23)
message (WARNING ${CMAKE_MODULE_PATH})

set(FluxCppCore ../../../../../../FluxCppCore/include/)

include_directories(${FluxCppCore})

add_executable(binary_data_parser main.cpp)