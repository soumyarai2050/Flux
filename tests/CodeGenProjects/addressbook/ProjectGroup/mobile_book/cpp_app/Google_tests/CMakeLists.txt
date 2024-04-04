cmake_minimum_required(VERSION 3.22)
set(CMAKE_CXX_STANDARD 23)
list(APPEND CMAKE_MODULE_PATH "../cmake")
message (WARNING ${CMAKE_MODULE_PATH})
project(Google_tests CXX)
find_package(Mongo REQUIRED)
find_package(Protobuf REQUIRED)
find_package(quill REQUIRED)

set(libabsl_ROOT_PATH  /usr/local/lib)
set(protobuf_lib ${libabsl_ROOT_PATH}/libprotobuf.a)
set(lib_utf ${libabsl_ROOT_PATH}/libutf8_validity.a)
set(protobuf_ABSL_USED_TARGETS ${libabsl_ROOT_PATH}/libabsl_log_severity.a ${libabsl_ROOT_PATH}/libabsl_raw_logging_internal.a
        ${libabsl_ROOT_PATH}/libabsl_bad_optional_access.a ${libabsl_ROOT_PATH}/libabsl_die_if_null.a
        ${libabsl_ROOT_PATH}/libabsl_hash.a ${libabsl_ROOT_PATH}/libabsl_bad_variant_access.a
        ${libabsl_ROOT_PATH}/libabsl_hashtablez_sampler.a ${libabsl_ROOT_PATH}/libabsl_low_level_hash.a
        ${libabsl_ROOT_PATH}/libabsl_spinlock_wait.a ${libabsl_ROOT_PATH}/libabsl_city.a
        ${libabsl_ROOT_PATH}/libabsl_leak_check.a ${libabsl_ROOT_PATH}/libabsl_civil_time.a
        ${libabsl_ROOT_PATH}/libabsl_flags.a ${libabsl_ROOT_PATH}/libabsl_log_entry.a ${libabsl_ROOT_PATH}/libabsl_status.a
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

include(FetchContent)
FetchContent_Declare(
        googletest
        # Specify the commit you depend on and update it regularly.
        URL https://github.com/google/googletest/archive/5376968f6948923e2411081fd9372e71a59d8e77.zip
)
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)

set(CppCodec ../../../../../../../Flux/CodeGenProjects/AddressBook/ProjectGroup/mobile_book/generated/CppCodec)
set(CppTest ../../../../../../../Flux/CodeGenProjects/AddressBook/ProjectGroup/mobile_book/generated/CppTest)
set(CppUtilGen ../../../../../../../Flux/CodeGenProjects/AddressBook/ProjectGroup/mobile_book/generated/CppUtilGen)
set(ProtoGenCc ../../../../../../../Flux/CodeGenProjects/AddressBook/ProjectGroup/mobile_book/generated/ProtoGenCc)
#set(FluxCodeGenCore ../../../../../Flux/PyCodeGenEngine/FluxCodeGenCore)
set(App ../../../../../../../Flux/CodeGenProjects/AddressBook/ProjectGroup/mobile_book/cpp_app/include)
set(FluxCppCore ../../../../../../../Flux/FluxCppCore/include)

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

target_link_libraries(Google_Tests_run gtest gtest_main ${MONGO_LIB} ${BSON_LIB} ${Protobuf_LIBRARIES}
        ${lib_utf}
        ${protobuf_ABSL_USED_TARGETS} quill::quill)