cmake_minimum_required(VERSION 3.22)

set(HOME $ENV{HOME})
set(LIBS_ROOT_DIR ${HOME}/cpp_libs/libs_13)

set(MONGO_INCLUDE_DIR "${LIBS_ROOT_DIR}/mongocxx/include/mongocxx/v_noabi")
set(BSON_INCLUDE_DIR "${LIBS_ROOT_DIR}/mongocxx/include/bsoncxx/v_noabi")
set(BSON_THIRD_PARTY_INCLUDE_DIR "${LIBS_ROOT_DIR}/mongocxx/include/bsoncxx/v_noabi/bsoncxx/third_party/mnmlstc/")
IF (APPLE)
    set(MONGO_LIB /usr/local/lib/libmongocxx.dylib)
    set(BSON_LIB /usr/local/lib/libbsoncxx.dylib)
ELSE()  # Other platforms
    set(MONGO_LIB ${LIBS_ROOT_DIR}/mongocxx/lib/libmongocxx.so._noabi)
    set(BSON_LIB ${LIBS_ROOT_DIR}/mongocxx/lib/libbsoncxx.so._noabi)
ENDIF()
