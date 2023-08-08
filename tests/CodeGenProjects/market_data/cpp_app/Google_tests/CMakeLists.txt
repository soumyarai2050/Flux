cmake_minimum_required(VERSION 3.22)
list(APPEND CMAKE_MODULE_PATH "../cmake")
message (WARNING ${CMAKE_MODULE_PATH})
find_package(Mongo REQUIRED)
find_package(Protobuf REQUIRED)
find_package(quill REQUIRED)

include(FetchContent)
FetchContent_Declare(
        googletest
        # Specify the commit you depend on and update it regularly.
        URL https://github.com/google/googletest/archive/5376968f6948923e2411081fd9372e71a59d8e77.zip
)
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)

set(CppCodec ../../../../../Flux/CodeGenProjects/market_data/generated/CppCodec)
set(CppTest ../../../../../Flux/CodeGenProjects/market_data/generated/CppTest)
set(CppMongoDBHandler ../../../../../Flux/CodeGenProjects/market_data/generated/CppMongoDBHandler)
set(CppUtilGen ../../../../../Flux/CodeGenProjects/market_data/generated/CppUtilGen)
set(ProtoGenCc ../../../../../Flux/CodeGenProjects/market_data/generated/ProtoGenCc)
#set(FluxCodeGenCore ../../../../../Flux/PyCodeGenEngine/FluxCodeGenCore)
set(App ../../../../../Flux/CodeGenProjects/market_data/cpp_app/cmake)

file(GLOB SRC_FILES ${CppCodec}/*)
file(GLOB SRC_FILES ${CppTest}/*)
file(GLOB SRC_FILES ${CppMongoDBHandler}/*)
file(GLOB SRC_FILES ${CppUtilGen}/*)
file(GLOB SRC_FILES ${ProtoGenCc}/*)
#file(GLOB SRC_FILES ${FluxCodeGenCore}/*)
file(GLOB SRC_FILES ${App}/*)

message(SRC_FILES ${SRC_FILES})

FetchContent_MakeAvailable(googletest)

project(Google_tests)
#add_subdirectory(lib)
message(WARNING ${MONGO_INCLUDE_DIR})
message(WARNING ${BSON_INCLUDE_DIR})

include_directories(${gtest_SOURCE_DIR}/include ${gtest_SOURCE_DIR} ${MONGO_INCLUDE_DIR} ${BSON_INCLUDE_DIR}
        ${Protobuf_INCLUDE_DIRS} ${CppCodec} ${CppTest} ${CppCodec} ${CppMongoDBHandler} ${CppUtilGen} ${ProtoGenCc} ${FluxCodeGenCore} ${${FluxCodeGenCore}} /usr/local/lib/quill)

set(MD_MODEL ../../../../../Flux/CodeGenProjects/market_data/model)
set(FLUX_MODEL ../../../../../Flux)
protobuf_generate_cpp(PROTO_HDRS PROTO_SRCS ${MD_MODEL}/dashboards_core.proto ${MD_MODEL}/market_data_core.proto ${MD_MODEL}/market_data_service.proto ${FLUX_MODEL}/trade_core.proto  ${FLUX_MODEL}/flux_utils.proto  ${FLUX_MODEL}/flux_options.proto  ${FLUX_MODEL}/ui_option_utils.proto  ${FLUX_MODEL}/ui_core.proto)


# adding the Google_Tests_run target
add_executable(Google_Tests_run DB_Test.cpp ${SRC_FILES})
# linking Google_Tests_run with DateConverter_lib which will be tested
#target_link_libraries(Google_Tests_run DateConverter_lib)

target_link_libraries(Google_Tests_run gtest gtest_main ${MONGO_LIB} ${BSON_LIB} ${Protobuf_LIBRARIES} quill::quill)