
#include "mobile_book_interface.h"

extern "C" void cpp_app_launcher(const char* yaml_config_file, const size_t yaml_config_fle_len) {
    GetCppAppLogger();
    std::string yaml_path(yaml_config_file, yaml_config_fle_len);
    mobile_book_consumer = std::make_shared<MobileBookConsumer>(yaml_path);
    std::thread cpp_app_launcher_thread([] {
        if (mobile_book_consumer) {
            mobile_book_consumer->go();
        }
    });
    cpp_app_launcher_thread.detach();
}
