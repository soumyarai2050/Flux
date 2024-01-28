cmake_minimum_required(VERSION 3.22)
project(mobile_book)

set(CMAKE_CXX_STANDARD 17)

set(BOOST_INCLUDE_DIR "/usr/local/include")

set(BOOST_LIB_DIR /usr/local/lib)

set(BOOST_LIB ${BOOST_LIB_DIR}/libboost_system.so ${BOOST_LIB_DIR}/libboost_thread.so ${BOOST_LIB_DIR}/libboost_regex.so)


find_package(Protobuf REQUIRED)

set(EXTERNAL_DIR1 ../generated/CppDBEncodeDecodeHandler)
set(EXTERNAL_DIR2 ../generated/CppDBHandler)
set(EXTERNAL_DIR3 ../generated/CppSerializeDeserialize)
set(EXTERNAL_DIR4 ../generated/ProtoGenCc)


include_directories(${Protobuf_INCLUDE_DIRS} ${BOOST_INCLUDE_DIR} ${EXTERNAL_DIR1}
        ${EXTERNAL_DIR2}
        ${EXTERNAL_DIR3}
        ${EXTERNAL_DIR4}
        )

protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS ../model/dashboards_core.proto ../model/mobile_book_core.proto ../model/mobile_book_service.proto ../../../ui_option_utils.proto ../../../ui_core.proto ../../../flux_utils.proto ../../../flux_options.proto ../../../trade_core.proto)
#protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS model/mobile_book_service3.proto)

add_executable(mobile_book main.cpp serialize_and_deserialize_using_proto2.cpp ${PROTO_SRCS} ${PROTO_HDRS})
#add_executable(mobile_book main.cpp serialize_and_deserialize_using_proto3.cpp ${PROTO_SRCS} ${PROTO_HDRS})

target_link_libraries(mobile_book ${Protobuf_LIBRARIES} ${BOOST_LIB})

