cmake_minimum_required(VERSION 3.22)
set(CMAKE_CXX_STANDARD 23)
list(APPEND CMAKE_MODULE_PATH "../cmake")
message (WARNING ${CMAKE_MODULE_PATH})
project(Google_tests CXX)
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

set(CppCodec ../../../../../Flux/CodeGenProjects/mobile_book/generated/CppCodec)
set(CppTest ../../../../../Flux/CodeGenProjects/mobile_book/generated/CppTest)
set(CppUtilGen ../../../../../Flux/CodeGenProjects/mobile_book/generated/CppUtilGen)
set(ProtoGenCc ../../../../../Flux/CodeGenProjects/mobile_book/generated/ProtoGenCc)
#set(FluxCodeGenCore ../../../../../Flux/PyCodeGenEngine/FluxCodeGenCore)
set(App ../../../../../Flux/CodeGenProjects/mobile_book/cpp_app/include)
set(FluxCppCore ../../../../../Flux/FluxCppCore/include)

file(GLOB CppCodec_SRC ${CppCodec}/*)
file(GLOB CppTest_SRC ${CppTest}/*)
file(GLOB CppUtilGen_SRC ${CppUtilGen}/*)
file(GLOB ProtoGenCc_SRC ${ProtoGenCc}/*)
file(GLOB App_SRC ${App}/*)
file(GLOB FluxCppCore_SRC ${FluxCppCore}/*)


FetchContent_MakeAvailable(googletest)

#add_subdirectory(lib)
message(WARNING ${MONGO_INCLUDE_DIR})
message(WARNING ${BSON_INCLUDE_DIR})

include_directories(${gtest_SOURCE_DIR}/include ${gtest_SOURCE_DIR} ${MONGO_INCLUDE_DIR} ${BSON_INCLUDE_DIR}
        ${Protobuf_INCLUDE_DIRS} ${CppCodec} ${CppTest} ${CppCodec} ${CppUtilGen} ${ProtoGenCc} ${App} ${FluxCppCore} /usr/local/lib/quill)

set(MD_MODEL ../../../../../Flux/CodeGenProjects/mobile_book/generated/CppProto2)
protobuf_generate_cpp(PROTO_HDRS PROTO_SRCS ${MD_MODEL}/dept_book_core.proto ${MD_MODEL}/mobile_book_core.proto ${MD_MODEL}/mobile_book_service.proto)

set(SRC_FILES
        ${CppCodec_SRC}
        ${CppTest_SRC}
        ${CppUtilGen_SRC}
        ${ProtoGenCc_SRC}
        ${App_SRC}
        ${FluxCppCore_SRC}
)

message(SRC_FILES ${SRC_FILES})

# Enable debugging symbols for the test executable
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g")

# adding the Google_Tests_run target
add_executable(Google_Tests_run DB_Test.cpp ${SRC_FILES})
# linking Google_Tests_run with DateConverter_lib which will be tested
#target_link_libraries(Google_Tests_run DateConverter_lib)

target_link_libraries(Google_Tests_run gtest gtest_main ${MONGO_LIB} ${BSON_LIB} ${Protobuf_LIBRARIES} quill::quill)