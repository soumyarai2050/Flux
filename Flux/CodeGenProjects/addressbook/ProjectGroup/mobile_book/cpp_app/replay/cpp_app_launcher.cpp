
#include "mobile_book_interface.h"

extern "C" void cpp_app_launcher(const char* yaml_config_file, const size_t yaml_config_fle_len) {
    std::string yaml_path(yaml_config_file, yaml_config_fle_len);
    std::thread cpp_app_launcher_thread([yaml_path] {
        mobile_book_consumer = new MobileBookConsumer(yaml_path);
        mobile_book_consumer->go();
    });

    cpp_app_launcher_thread.detach();
}
