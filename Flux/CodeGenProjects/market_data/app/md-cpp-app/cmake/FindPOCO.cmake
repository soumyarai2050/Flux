cmake_minimum_required(VERSION 3.22)
set(POCO_INCLUDE_DIR "/usr/local/include")
set(POCO_LIB_DIR /usr/local/lib)

IF (APPLE)
    set(POCO_LIB ${POCO_LIB_DIR}/libPocoNet.dylib ${POCO_LIB_DIR}/libPocoFoundation.dylib ${POCO_LIB_DIR}/libPocoJSON.dylib ${POCO_LIB_DIR}/libPocoUtil.dylib)
ELSE()  # Other platforms
    set(POCO_LIB ${POCO_LIB_DIR}/libPocoNet.so ${POCO_LIB_DIR}/libPocoNetSSL.so ${POCO_LIB_DIR}/libPocoFoundation.so ${POCO_LIB_DIR}/libPocoJSON.so ${POCO_LIB_DIR}/libPocoUtil.so)
ENDIF()
