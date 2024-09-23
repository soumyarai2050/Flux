
#include "mongo_db_singleton.h"
#include "mobile_book_consumer.h"
#include "mock_mobile_book_cache.h"
#include "cpp_app_shared_resource.h"

extern "C" void cpp_app_launcher() {

    std::thread cpp_app_launcher_thread([&] {
        const char* config_file = getenv("simulate_config_yaml_file");
        if (!config_file) {
            throw std::runtime_error("export env variable {simulate_config_yaml_file}");
        }
        if (access(config_file, F_OK) != 0) {
            throw std::runtime_error(std::format("{} not accessable", config_file));
        }

        YAML::Node config = YAML::LoadFile(config_file);
        auto db_uri = config["mongo_server"].as<std::string>();
        auto db_name = config["db_name"].as<std::string>();
        auto db = MongoDBHandlerSingleton::get_instance(db_uri, db_name);
        MobileBookInterface* mobile_book_cons = new MobileBookConsumer(config, db, top_of_book_websocket_server,
        last_barter_websocket_server, market_depth_websocket_server);
        mobile_book_cons->go();
    });

    cpp_app_launcher_thread.detach();
}
