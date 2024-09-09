
#include "mongo_db_singleton.h"
#include "mobile_book_consumer.h"
#include "mock_mobile_book_cache.h"
#include "cpp_app_shared_resource.h"

extern "C" void cpp_app_launcher() {

    std::thread cpp_app_launcher_thread([&] {
        std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db = MongoDBHandlerSingleton::get_instance();
        MobileBookInterface* mobile_book_cons = new MobileBookConsumer(sp_mongo_db, top_of_book_websocket_server,
        last_barter_websocket_server, market_depth_websocket_server);
        mobile_book_cons->go();
    });

    cpp_app_launcher_thread.detach();
}
