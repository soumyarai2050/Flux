cmake_minimum_required(VERSION 3.22)
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
message (WARNING ${CMAKE_MODULE_PATH})
find_package(Mongo REQUIRED)
find_package(POCO REQUIRED)
find_package(RapidJSON REQUIRED)

include(FetchContent)
FetchContent_Declare(
        googletest
        # Specify the commit you depend on and update it regularly.
        URL https://github.com/google/googletest/archive/5376968f6948923e2411081fd9372e71a59d8e77.zip
)
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

project(Google_tests)
#add_subdirectory(lib)
message(WARNING ${MONGO_INCLUDE_DIR})
message(WARNING ${BSON_INCLUDE_DIR})

include_directories(${gtest_SOURCE_DIR}/include ${gtest_SOURCE_DIR} ${MONGO_INCLUDE_DIR} ${BSON_INCLUDE_DIR} ${POCO_INCLUDE_DIR} ${RapidJSON_INCLUDE_DIR})

# adding the Google_Tests_run target
add_executable(Google_Tests_run MD_Test.cpp)

# linking Google_Tests_run with DateConverter_lib which will be tested
#target_link_libraries(Google_Tests_run DateConverter_lib)

target_link_libraries(Google_Tests_run gtest gtest_main ${MONGO_LIB} ${BSON_LIB} ${POCO_LIB})