#include <iostream>
#include <string>

#include "cpp_app_shared_resource.h"
#include "base_web_server.h"
#include "../include/config_parser.h"
#include "mobile_book_consumer.h"

int main(int argc, char *argv[]) {
    signal(SIGINT, signal_handler);
    signal(SIGKILL, signal_handler);
    signal(SIGTERM, signal_handler);

    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " config_file" << std::endl;
        return 1; // Return an error code
    }
    std::string config_file = argv[1];
    Config config(config_file); // Use std::string directly
    MobileBookConsumer mobile_book_consumer(config);
    FluxCppCore::BaseWebServer http_server(host, config.m_http_server_port_, mobile_book_consumer);
    std::jthread http_server_thread{&FluxCppCore::BaseWebServer::run, &http_server};
    mobile_book_consumer.go();

    return 0; // Return success code
}
