#include <iostream>
#include <string>

#include "cpp_app_shared_resource.h"
#include "../include/config_parser.h"
#include "mobile_book_consumer.h"

#include "mobile_book_web_server_routes.h"

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
    std::shared_ptr<FluxCppCore::MongoDBHandler> mongo_db_handler = std::make_shared<FluxCppCore::MongoDBHandler>(config.m_mongodb_uri_, config.m_db_name_);
    MobileBookPublisher mobile_book_publisher(config, mongo_db_handler);
    mobile_book_consumer = std::make_unique<MobileBookConsumer>(config, mobile_book_publisher);

    MobileBookWebServer http_server(config, mobile_book_publisher);

    mobile_book_consumer->init_shm();
    mobile_book_consumer->go();

     while (keepRunning.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    http_server.cleanup();
    return 0; // Return success code
}
