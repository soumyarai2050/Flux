cmake_minimum_required(VERSION 3.22)
project(phone_book)

set(CMAKE_CXX_STANDARD 17)

find_package(Protobuf REQUIRED)

set(EXTERNAL_DIR1 ../generated/CppDBEncodeDecodeHandler)
set(EXTERNAL_DIR2 ../generated/CppDBHandler)
set(EXTERNAL_DIR3 ../generated/CppSerializeDeserialize)
set(EXTERNAL_DIR4 ../generated/ProtoGenCc)

include_directories(${Protobuf_INCLUDE_DIRS} ${EXTERNAL_DIR1}
        ${EXTERNAL_DIR2}
        ${EXTERNAL_DIR3}
        ${EXTERNAL_DIR4})


protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS ../model/plan_core.proto ../model/email_book_service.proto ../../../ui_option_utils.proto ../../../ui_core.proto ../../../flux_utils.proto ../../../flux_options.proto ../../../barter_core.proto)
#protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS model/email_book_service3.proto)

add_executable(phone_book main.cpp serialize_and_deserialize_using_proto2.cpp ${PROTO_SRCS} ${PROTO_HDRS})
#add_executable(phone_book main.cpp serialize_and_deserialize_using_proto3.cpp ${PROTO_SRCS} ${PROTO_HDRS})

target_link_libraries(phone_book ${Protobuf_LIBRARIES})
