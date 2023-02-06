cmake_minimum_required(VERSION 3.22)
project(Mongo)

set(CMAKE_CXX_STANDARD 17)

add_executable(Mongo store_depth_market_data.cpp pre_agregation.cpp)


# Include the mongocxx headers
include_directories(/usr/local/include/bsoncxx/v_noabi /usr/local/include/mongocxx/v_noabi)


set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_RPATH}:/usr/local/lib")

#add_executable(mongocxx_example main.cpp)
link_directories(Mongo ${CMAKE_INSTALL_RPATH})

# Include POCO headers
include_directories(/usr/local/include)

# Set the library directory for POCO
set(POCO_LIB_DIR /usr/local/lib)

# Link the mongocxx library to the executable
# UNIX
IF (APPLE)
    target_link_libraries(Mongo /usr/local/lib/libmongocxx.dylib)
    target_link_libraries(Mongo /usr/local/lib/libbsoncxx.dylib)
    # Link the POCO libraries to the Mongo target
    target_link_libraries(Mongo ${POCO_LIB_DIR}/libPocoNet.dylib ${POCO_LIB_DIR}/libPocoFoundation.dylib ${POCO_LIB_DIR}/libPocoJSON.dylib ${POCO_LIB_DIR}/libPocoUtil.dylib)

ELSE()  # Other platforms
    target_link_libraries(Mongo /usr/local/lib/libmongocxx.so._noabi)
    target_link_libraries(Mongo /usr/local/lib/libbsoncxx.so._noabi)
    # Link the POCO libraries to the Mongo target
    target_link_libraries(Mongo ${POCO_LIB_DIR}/libPocoNet.so ${POCO_LIB_DIR}/libPocoNetSSL.so ${POCO_LIB_DIR}/libPocoFoundation.so ${POCO_LIB_DIR}/libPocoJSON.so ${POCO_LIB_DIR}/libPocoUtil.so)
ENDIF()

