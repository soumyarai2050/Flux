cmake_minimum_required(VERSION 3.22)
set(MONGO_INCLUDE_DIR "/usr/local/include/mongocxx/v_noabi")
set(BSON_INCLUDE_DIR "/usr/local/include/bsoncxx/v_noabi")
IF (APPLE)
    set(MONGO_LIB /usr/local/lib/libmongocxx.dylib)
    set(BSON_LIB /usr/local/lib/libbsoncxx.dylib)
ELSE()  # Other platforms
    set(MONGO_LIB /usr/local/lib/libmongocxx.so._noabi)
    set(BSON_LIB /usr/local/lib/libbsoncxx.so._noabi)
ENDIF()