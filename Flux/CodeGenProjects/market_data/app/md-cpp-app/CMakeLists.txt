cmake_minimum_required(VERSION 3.22)
set(CMAKE_CXX_STANDARD 17)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake/")
message (WARNING ${CMAKE_MODULE_PATH})
find_package(Mongo REQUIRED)
find_package(POCO REQUIRED)
find_package(RapidJSON REQUIRED)

project(md_handler)
#include(CTest)
add_subdirectory(Google_tests)
# Now simply link against gtest or gtest_main as needed. Eg
#add_executable(example example.cpp)
#target_link_libraries(example gtest_main)
#add_test(NAME example_test COMMAND example)
enable_testing()
add_executable(md_handler src/MD_Replay.cpp src/MD_PreAgregation.cpp src/MD_TopOfBookPublisher.cpp)


set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_RPATH}:/usr/local/lib")

link_directories(md_handler ${CMAKE_INSTALL_RPATH})

# Include POCO headers from /usr/local/include
include_directories(${MONGO_INCLUDE_DIR} ${BSON_INCLUDE_DIR} ${POCO_INCLUDE_DIR} ${RapidJSON_INCLUDE_DIR})
target_link_libraries(md_handler ${MONGO_LIB} ${BSON_LIB} ${POCO_LIB})


