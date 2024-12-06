cmake_minimum_required(VERSION 3.28)
project(global_interpreter_lock)

set(CMAKE_CXX_STANDARD 17)

include_directories(/usr/include/python3.12)

add_executable(global_interpreter_lock main.cpp)

target_compile_options(global_interpreter_lock PRIVATE -g -ggdb3 -Werror -Wall -Wextra -Wno-deprecated-declarations -Wno-error=unused-parameter)

target_link_libraries(global_interpreter_lock /usr/lib/x86_64-linux-gnu/libpython3.12.so)