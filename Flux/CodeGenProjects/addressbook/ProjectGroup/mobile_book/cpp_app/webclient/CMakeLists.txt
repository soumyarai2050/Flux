cmake_minimum_required(VERSION 3.22)
set(CMAKE_CXX_STANDARD 23)
list(APPEND CMAKE_MODULE_PATH "../cmake/")
message (WARNING ${CMAKE_MODULE_PATH})
find_package(Mongo REQUIRED)
find_package(Protobuf REQUIRED)
find_package(quill REQUIRED)

set(CppCodec ../../generated/CppCodec)
set(CppTest ../../generated/generated/CppTest)
set(CppUtilGen ../../generated/CppUtilGen)
set(ProtoGenCc ../../generated/ProtoGenCc)
set(PhoneBookProtoGenCc ../../../phone_book/generated/ProtoGenCc)
set(FluxCppCore ../../../../../../FluxCppCore/include/)

file(GLOB CppCodec_SRC ${CppCodec}/*)
file(GLOB CppTest_SRC ${CppTest}/*)
file(GLOB CppUtilGen_SRC ${CppUtilGen}/*)
file(GLOB ProtoGenCc_SRC ${ProtoGenCc}/*)
file(GLOB PhoneBookProtoGenCc_SRC ${PhoneBookProtoGenCc}/*)
#file(GLOB App_SRC ${App}/*)
file(GLOB FluxCppCore_SRC ${FluxCppCore}/*)

project(mobile_book_web_client)

message(WARNING ${MONGO_INCLUDE_DIR})
message(WARNING ${BSON_INCLUDE_DIR})

include_directories(${gtest_SOURCE_DIR}/include ${gtest_SOURCE_DIR} ${MONGO_INCLUDE_DIR} ${BSON_INCLUDE_DIR}
        ${Protobuf_INCLUDE_DIRS} ${CppCodec} ${CppTest} ${CppCodec} ${CppUtilGen} ${ProtoGenCc} ${PhoneBookProtoGenCc}  ${FluxCppCore} /usr/local/lib/quill)

set(MD_MODEL ../../generated/CppProto2)
set(Pair_Strat_Model ../../../phone_book/generated/CppProto2)
protobuf_generate_cpp(PROTO_HDRS PROTO_SRCS
        ${MD_MODEL}/mobile_book_service.proto ${Pair_Strat_Model}/strat_core.proto ${Pair_Strat_Model}/email_book_service.proto)

set(SRC_FILES
        ${CppCodec_SRC}
        ${CppTest_SRC}
        ${CppUtilGen_SRC}
        ${ProtoGenCc_SRC}
        ${PhoneBookProtoGenCc_SRC}
        ${FluxCppCore_SRC}
)

message(SRC_FILES ${SRC_FILES})

add_executable(mobile_book_web_client main.cpp ${SRC_FILES})
target_compile_options(mobile_book_web_client PRIVATE -g)

target_link_libraries(mobile_book_web_client ${MONGO_LIB} ${BSON_LIB} ${Protobuf_LIBRARIES} quill::quill)
