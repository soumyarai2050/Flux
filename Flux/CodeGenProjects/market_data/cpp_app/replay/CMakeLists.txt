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
#set(FluxCodeGenCore ../../../../../Flux/PyCodeGenEngine/FluxCodeGenCore)
#set(App ../../../../../Flux/CodeGenProjects/market_data/cpp_app/include)
set(FluxCppCore ../../../../../Flux/FluxCppCore/include)

file(GLOB CppCodec_SRC ${CppCodec}/*)
file(GLOB CppTest_SRC ${CppTest}/*)
file(GLOB CppUtilGen_SRC ${CppUtilGen}/*)
file(GLOB ProtoGenCc_SRC ${ProtoGenCc}/*)
#file(GLOB App_SRC ${App}/*)
file(GLOB FluxCppCore_SRC ${FluxCppCore}/*)

project(market_data)

message(WARNING ${MONGO_INCLUDE_DIR})
message(WARNING ${BSON_INCLUDE_DIR})

include_directories(${gtest_SOURCE_DIR}/include ${gtest_SOURCE_DIR} ${MONGO_INCLUDE_DIR} ${BSON_INCLUDE_DIR}
        ${Protobuf_INCLUDE_DIRS} ${CppCodec} ${CppTest} ${CppCodec} ${CppUtilGen} ${ProtoGenCc}  ${FluxCppCore} /usr/local/lib/quill)

set(MD_MODEL ../../generated/CppProto2)
protobuf_generate_cpp(PROTO_HDRS PROTO_SRCS ${MD_MODEL}/market_data_service.proto)

set(SRC_FILES
        ${CppCodec_SRC}
        ${CppTest_SRC}
        ${CppUtilGen_SRC}
        ${ProtoGenCc_SRC}
        ${FluxCppCore_SRC}
)

message(SRC_FILES ${SRC_FILES})

add_executable(market_data main.cpp ${SRC_FILES})
target_compile_options(market_data PRIVATE -g)

target_link_libraries(market_data ${MONGO_LIB} ${BSON_LIB} ${Protobuf_LIBRARIES} quill::quill)
