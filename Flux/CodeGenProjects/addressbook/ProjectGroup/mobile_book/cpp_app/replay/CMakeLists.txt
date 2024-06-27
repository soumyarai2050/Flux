cmake_minimum_required(VERSION 3.22)
set(CMAKE_CXX_STANDARD 23)
list(APPEND CMAKE_MODULE_PATH "../cmake/")
message (WARNING ${CMAKE_MODULE_PATH})
find_package(Mongo REQUIRED)
#find_package(Protobuf REQUIRED)
#find_package(quill REQUIRED)
find_package(Python REQUIRED COMPONENTS Development)

set(libabsl_ROOT_PATH  /home/subham/cpp_libs/libs_13/protobuf_25.2/lib)
set(ABSL_INCLUDE_DIR /home/subham/cpp_libs/libs_13/protobuf_25.2/include)

set(CPP_YAML_INCLUDE_DIR /home/subham/cpp_libs/libs_13/cpp_yaml/include/)
set(CPP_YAML_LIB /home/subham/cpp_libs/libs_13/cpp_yaml/lib/libyaml-cpp.so)

set(protobuf_lib ${libabsl_ROOT_PATH}/libprotobuf.a)
set(lib_utf ${libabsl_ROOT_PATH}/libutf8_validity.a)

set(protobuf_ABSL_USED_TARGETS ${libabsl_ROOT_PATH}/libabsl_log_severity.a ${libabsl_ROOT_PATH}/libabsl_raw_logging_internal.a
        ${libabsl_ROOT_PATH}/libabsl_bad_optional_access.a ${libabsl_ROOT_PATH}/libabsl_die_if_null.a
        ${libabsl_ROOT_PATH}/libabsl_hash.a ${libabsl_ROOT_PATH}/libabsl_bad_variant_access.a
        ${libabsl_ROOT_PATH}/libabsl_hashtablez_sampler.a ${libabsl_ROOT_PATH}/libabsl_low_level_hash.a
        ${libabsl_ROOT_PATH}/libabsl_spinlock_wait.a ${libabsl_ROOT_PATH}/libabsl_city.a
        ${libabsl_ROOT_PATH}/libabsl_leak_check.a ${libabsl_ROOT_PATH}/libabsl_civil_time.a
         ${libabsl_ROOT_PATH}/libabsl_log_entry.a ${libabsl_ROOT_PATH}/libabsl_status.a
        ${libabsl_ROOT_PATH}/libabsl_cord.a ${libabsl_ROOT_PATH}/libabsl_flags_commandlineflag.a
        ${libabsl_ROOT_PATH}/libabsl_statusor.a ${libabsl_ROOT_PATH}/libabsl_cord_internal.a
        ${libabsl_ROOT_PATH}/libabsl_flags_commandlineflag_internal.a ${libabsl_ROOT_PATH}/libabsl_log_globals.a
        ${libabsl_ROOT_PATH}/libabsl_statusor.a ${libabsl_ROOT_PATH}/libabsl_cordz_functions.a
        ${libabsl_ROOT_PATH}/libabsl_exponential_biased.a ${libabsl_ROOT_PATH}/libabsl_flags_config.a
        ${libabsl_ROOT_PATH}/libabsl_log_initialize.a ${libabsl_ROOT_PATH}/libabsl_str_format_internal.a
        ${libabsl_ROOT_PATH}/libabsl_flags_internal.a ${libabsl_ROOT_PATH}/libabsl_log_internal_check_op.a
        ${libabsl_ROOT_PATH}/libabsl_log_internal_nullguard.a
        ${libabsl_ROOT_PATH}/libabsl_strings.a ${libabsl_ROOT_PATH}/libabsl_cordz_info.a
        ${libabsl_ROOT_PATH}/libabsl_cordz_handle.a ${libabsl_ROOT_PATH}/libabsl_flags_marshalling.a
        ${libabsl_ROOT_PATH}/libabsl_log_internal_conditions.a ${libabsl_ROOT_PATH}/libabsl_strings_internal.a
        ${libabsl_ROOT_PATH}/libabsl_flags_private_handle_accessor.a ${libabsl_ROOT_PATH}/libabsl_synchronization.a
        ${libabsl_ROOT_PATH}/libabsl_kernel_timeout_internal.a
        ${libabsl_ROOT_PATH}/libabsl_graphcycles_internal.a
        ${libabsl_ROOT_PATH}/libabsl_symbolize.a
        ${libabsl_ROOT_PATH}/libabsl_demangle_internal.a ${libabsl_ROOT_PATH}/libabsl_crc_cord_state.a
        ${libabsl_ROOT_PATH}/libabsl_crc32c.a ${libabsl_ROOT_PATH}/libabsl_flags_program_name.a
        ${libabsl_ROOT_PATH}/libabsl_throw_delegate.a ${libabsl_ROOT_PATH}/libabsl_crc_cpu_detect.a
        ${libabsl_ROOT_PATH}/libabsl_flags_reflection.a ${libabsl_ROOT_PATH}/libabsl_log_internal_message.a
        ${libabsl_ROOT_PATH}/libabsl_strerror.a
        ${libabsl_ROOT_PATH}/libabsl_log_internal_format.a ${libabsl_ROOT_PATH}/libabsl_examine_stack.a
        ${libabsl_ROOT_PATH}/libabsl_log_globals.a ${libabsl_ROOT_PATH}/libabsl_log_internal_globals.a
        ${libabsl_ROOT_PATH}/libabsl_log_internal_log_sink_set.a ${libabsl_ROOT_PATH}/libabsl_log_sink.a
        ${libabsl_ROOT_PATH}/libabsl_time.a
        ${libabsl_ROOT_PATH}/libabsl_time_zone.a
        ${libabsl_ROOT_PATH}/libabsl_crc_internal.a
        ${libabsl_ROOT_PATH}/libabsl_log_internal_proto.a ${libabsl_ROOT_PATH}/libabsl_raw_hash_set.a
        ${libabsl_ROOT_PATH}/libabsl_malloc_internal.a ${libabsl_ROOT_PATH}/libabsl_stacktrace.a
        ${libabsl_ROOT_PATH}/libabsl_debugging_internal.a ${libabsl_ROOT_PATH}/libabsl_int128.a
        ${libabsl_ROOT_PATH}/libabsl_base.a)

set(Boost_INCLUDE_DIRS /home/subham/cpp_libs/libs_13/boost/include)
set(Boost_INCLUDE_LIBS /home/subham/cpp_libs/libs_13/boost/lib)
set(Boost_INCLUDE_LIBS_TARGET ${Boost_INCLUDE_LIBS}/libboost_atomic.so ${Boost_INCLUDE_LIBS}/libboost_chrono.so
         ${Boost_INCLUDE_LIBS}/libboost_container.so ${Boost_INCLUDE_LIBS}/libboost_context.so
         ${Boost_INCLUDE_LIBS}/libboost_contract.so ${Boost_INCLUDE_LIBS}/libboost_coroutine.so
         ${Boost_INCLUDE_LIBS}/libboost_date_time.so ${Boost_INCLUDE_LIBS}/libboost_fiber.so
         ${Boost_INCLUDE_LIBS}/libboost_filesystem.so ${Boost_INCLUDE_LIBS}/libboost_graph.so
         ${Boost_INCLUDE_LIBS}/libboost_iostreams.so ${Boost_INCLUDE_LIBS}/libboost_json.so
         ${Boost_INCLUDE_LIBS}/libboost_locale.so ${Boost_INCLUDE_LIBS}/libboost_log_setup.so
         ${Boost_INCLUDE_LIBS}/libboost_log.so ${Boost_INCLUDE_LIBS}/libboost_nowide.so
         ${Boost_INCLUDE_LIBS}/libboost_prg_exec_monitor.so ${Boost_INCLUDE_LIBS}/libboost_program_options.so
         ${Boost_INCLUDE_LIBS}/libboost_serialization.so ${Boost_INCLUDE_LIBS}/libboost_stacktrace_addr2line.so
         ${Boost_INCLUDE_LIBS}/libboost_stacktrace_backtrace.so ${Boost_INCLUDE_LIBS}/libboost_stacktrace_basic.so
         ${Boost_INCLUDE_LIBS}/libboost_stacktrace_noop.so ${Boost_INCLUDE_LIBS}/libboost_system.so
         ${Boost_INCLUDE_LIBS}/libboost_thread.so ${Boost_INCLUDE_LIBS}/libboost_timer.so
         ${Boost_INCLUDE_LIBS}/libboost_type_erasure.so ${Boost_INCLUDE_LIBS}/libboost_url.so ${Boost_INCLUDE_LIBS}/libboost_wave.so
         ${Boost_INCLUDE_LIBS}/libboost_wserialization.so
         )

set(CppCodec ../../generated/CppCodec)
set(CppTest ../../generated/generated/CppTest)
set(CppUtilGen ../../generated/CppUtilGen)
set(ProtoGenCc ../../generated/ProtoGenCc)
set(FluxCppCore ../../../../../../FluxCppCore/include/)

file(GLOB CppCodec_SRC ${CppCodec}/*.cpp)
#file(GLOB CppTest_SRC ${CppTest}/*.cpp)
file(GLOB CppUtilGen_SRC ${CppUtilGen}/*.cpp)
file(GLOB ProtoGenCc_SRC ${ProtoGenCc}/*.cc)
file(GLOB FluxCppCore_SRC ${FluxCppCore}/*.cpp)

project(mobile_book)

message(WARNING ${MONGO_INCLUDE_DIR})
message(WARNING ${BSON_INCLUDE_DIR})

include_directories(${MONGO_INCLUDE_DIR} ${BSON_THIRD_PARTY_INCLUDE_DIR} ${BSON_INCLUDE_DIR} ${Boost_INCLUDE_DIRS}
        ${Protobuf_INCLUDE_DIRS} ${ABSL_INCLUDE_DIR} ${CppCodec} ${CppCodec} ${CppUtilGen} ${ProtoGenCc}  ${FluxCppCore}
        /home/subham/cpp_libs/libs_13/quill/include /usr/include/python3.12 ${CPP_YAML_INCLUDE_DIR})

set(MD_MODEL ../../generated/CppProto2)
# protobuf_generate_cpp(PROTO_HDRS PROTO_SRCS ${MD_MODEL}/mobile_book_service.proto)

set(SRC_FILES
        ${CppCodec_SRC}
        ${CppUtilGen_SRC}
        ${ProtoGenCc_SRC}
        ${FluxCppCore_SRC}
)

message(SRC_FILES ${SRC_FILES})
message(${Python_LIBRARIES})
# Create shared library including dependencies
add_library(marketdataprovider SHARED ${SRC_FILES} cpp_app_launcher.cpp
        cpp_app_semaphore.cpp
        mongo_db_singleton.cpp
        mock_mobile_book_cache.cpp
        cpp_app_shared_resource.cpp
        add_or_get_container_from_py_cache.cpp)

# Link dependencies to the shared library
target_link_libraries(marketdataprovider
        /usr/lib/x86_64-linux-gnu/libpython3.12.so
        ${MONGO_LIB}
        ${BSON_LIB}
        ${protobuf_lib}
        ${lib_utf}
        ${protobuf_ABSL_USED_TARGETS}
        /home/subham/cpp_libs/libs_13/quill/lib/libquill.a
        ${Boost_INCLUDE_LIBS_TARGET}
        ${CPP_YAML_LIB}
)

# Add compile options to the shared library
target_compile_options(marketdataprovider PRIVATE -g -ggdb3 -Werror -Wall -Wextra -Wno-deprecated-declarations -Wno-unused-variable -Wno-error=unused-parameter)

# Create executable
add_executable(mobile_book_exec main.cpp ${SRC_FILES} cpp_app_semaphore.cpp
        mongo_db_singleton.cpp cpp_app_shared_resource.cpp add_or_get_container_from_py_cache.cpp
        mock_mobile_book_cache.cpp
)

target_compile_options(mobile_book_exec PRIVATE -g -ggdb3 -Werror -Wall -Wextra -Wno-deprecated-declarations -Wno-error=unused-parameter)
## Link the shared library to the executable
target_link_libraries(mobile_book_exec
        /usr/lib/x86_64-linux-gnu/libpython3.12.so
        ${MONGO_LIB}
        ${BSON_LIB}
        ${protobuf_lib}
        ${lib_utf}
        ${protobuf_ABSL_USED_TARGETS}
        /home/subham/cpp_libs/libs_13/quill/lib/libquill.a
        ${Boost_INCLUDE_LIBS_TARGET}
        ${CPP_YAML_LIB}
        )

# Link the shared library to the executable
#target_link_libraries(mobile_book_exec mobile_book)