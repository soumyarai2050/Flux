
cmake_minimum_required(VERSION 3.22)
set(CMAKE_CXX_STANDARD 23)
# Custom FindProtobuf script
# Searches for Protobuf in /usr/local

find_path(PROTOBUF_INCLUDE_DIRS google/protobuf/message.h HINTS /usr/local/include)
find_library(PROTOBUF_LIBRARIES protobuf HINTS /usr/local/lib)

if (PROTOBUF_INCLUDE_DIRS AND PROTOBUF_LIBRARIES)
    set(PROTOBUF_FOUND TRUE)
else ()
    set(PROTOBUF_FOUND FALSE)
endif ()

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(Protobuf DEFAULT_MSG PROTOBUF_LIBRARIES PROTOBUF_INCLUDE_DIRS)

mark_as_advanced(PROTOBUF_INCLUDE_DIRS PROTOBUF_LIBRARIES)
