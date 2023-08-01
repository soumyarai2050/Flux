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

set(EXTERNAL_DIR1 ../../../../../Flux/CodeGenProjects/market_data/generated/CppCodec ../../../../../Flux/CodeGenProjects/market_data/generated/CppTest)
set(EXTERNAL_DIR2 ../../../../../Flux/CodeGenProjects/market_data/generated/CppMongoDBHandler)
set(EXTERNAL_DIR3 ../../../../../Flux/CodeGenProjects/market_data/generated/CppUtilGen)
set(EXTERNAL_DIR4 ../../../../../Flux/CodeGenProjects/market_data/generated/ProtoGenCc)
set(EXTERNAL_DIR5 ../../../../../Flux/PyCodeGenEngine/FluxCodeGenCore ../../../../../Flux/CodeGenProjects/market_data/cpp_app/include)

set(EXTERNAL_CPP1 ../../../../../Flux/CodeGenProjects/market_data/generated/ProtoGenCc/dashboards_core.pb.cc)
set(EXTERNAL_CPP2 ../../../../../Flux/CodeGenProjects/market_data/generated/ProtoGenCc/market_data_core.pb.cc)
set(EXTERNAL_CPP3 ../../../../../Flux/CodeGenProjects/market_data/generated/ProtoGenCc/market_data_service.pb.cc)
set(EXTERNAL_CPP4 ../../../../../Flux/PyCodeGenEngine/FluxCodeGenCore/ui_core.pb.cc)
set(EXTERNAL_CPP5 ../../../../../Flux/PyCodeGenEngine/FluxCodeGenCore/flux_options.pb.cc)
set(EXTERNAL_CPP6 ../../../../../Flux/PyCodeGenEngine/FluxCodeGenCore/flux_utils.pb.cc)
set(EXTERNAL_CPP7 ../../../../../Flux/PyCodeGenEngine/FluxCodeGenCore/trade_core.pb.cc )

FetchContent_MakeAvailable(googletest)

project(Google_tests)
#add_subdirectory(lib)
message(WARNING ${MONGO_INCLUDE_DIR})
message(WARNING ${BSON_INCLUDE_DIR})

include_directories(${gtest_SOURCE_DIR}/include ${gtest_SOURCE_DIR} ${MONGO_INCLUDE_DIR} ${BSON_INCLUDE_DIR}
        ${Protobuf_INCLUDE_DIRS} ${EXTERNAL_DIR1} ${EXTERNAL_DIR2} ${EXTERNAL_DIR3} ${EXTERNAL_DIR4}
        ${EXTERNAL_DIR5} /usr/local/lib/quill
        )

protobuf_generate_cpp(PROTO_HDRS PROTO_SRCS ../../../../../Flux/CodeGenProjects/market_data/model/dashboards_core.proto ../../../../../Flux/CodeGenProjects/market_data/model/market_data_core.proto ../../../../../Flux/CodeGenProjects/market_data/model/market_data_service.proto ../../../../../Flux/trade_core.proto ../../../../../Flux/flux_utils.proto ../../../../../Flux/flux_options.proto ../../../../../Flux/ui_core.proto)


# adding the Google_Tests_run target
add_executable(Google_Tests_run DB_Test.cpp ${EXTERNAL_CPP1} ${EXTERNAL_CPP2} ${EXTERNAL_CPP3} ${EXTERNAL_CPP4} ${EXTERNAL_CPP5} ${EXTERNAL_CPP6} ${EXTERNAL_CPP7})

# linking Google_Tests_run with DateConverter_lib which will be tested
#target_link_libraries(Google_Tests_run DateConverter_lib)

target_link_libraries(Google_Tests_run gtest gtest_main ${MONGO_LIB} ${BSON_LIB} ${Protobuf_LIBRARIES} quill::quill)