#include <iostream>
#include <string>

#include "cpp_app_shared_resource.h"
#include "../include/base_web_server.h"
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
    mobile_book_consumer = std::make_unique<MobileBookConsumer>(config);
    FluxCppCore::BaseWebServer http_server(host, config.m_http_server_port_, *mobile_book_consumer);
    mobile_book_consumer->init_shm();
    std::thread http_server_thread{&FluxCppCore::BaseWebServer::run, &http_server};
    mobile_book_consumer->go();

     while (!shutdown_db_n_ws_thread.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    http_server.cleanup();
    http_server_thread.join();
    return 0; // Return success code
}
