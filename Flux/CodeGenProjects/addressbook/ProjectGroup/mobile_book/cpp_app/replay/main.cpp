#include <iostream>
#include <memory>
#include <string>

#include "cpp_app_shared_resource.h"
#include "mobile_book_interface.h"
#include "base_web_server.h"

int main(int argc, char *argv[]) {
    signal(SIGINT, signal_handler);
    signal(SIGKILL, signal_handler);
    signal(SIGTERM, signal_handler);

    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " config_file" << std::endl;
        return 1; // Return an error code
    }
    std::string config_file = argv[1];
    config = std::make_unique<Config>(config_file.c_str()); // Use std::string directly
    mobile_book_consumer = std::make_shared<MobileBookConsumer>(*config);
    FluxCppCore::BaseWebServer http_server(host, config->m_http_server_port_, *mobile_book_consumer);
    std::jthread http_server_thread{&FluxCppCore::BaseWebServer::run, &http_server};
    mobile_book_consumer->go();

    return 0; // Return success code
}
