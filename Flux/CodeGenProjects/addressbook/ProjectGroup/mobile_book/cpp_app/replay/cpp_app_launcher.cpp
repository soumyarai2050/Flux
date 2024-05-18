#include "last_barter_handler.h"
#include "market_depth_handler.h"
#include "history_manager.h"
#include "cpp_app_semaphore.h"
#include "mongo_db_singleton.h"
#include "top_of_book_handler.h"
#include "mobile_book_cache.h"
#include "mock_mobile_book_cache.h"

extern "C" void cpp_app_launcher() {

    std::thread cpp_app_launcher_thread([&] {
        quill::start();
        std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db = MongoDBHandlerSingleton::get_instance();
        mobile_book_cache::MarketDepthCache marketDepthCache;
        mobile_book_cache::TopOfBookCache topOfBookCache;
        mobile_book_cache::LastBarterCache lastBarterCache;
        mobile_book_handler::TopOfBookHandler top_of_book_handler(sp_mongo_db, top_of_book_websocket_server);
        mobile_book_handler::MarketDepthHandler market_depth_handler(sp_mongo_db, market_depth_websocket_server,
            top_of_book_handler, marketDepthCache, topOfBookCache);
        mobile_book_handler::LastBarterHandler last_barter_handler(sp_mongo_db, last_barter_websocket_server,
            top_of_book_handler, lastBarterCache, topOfBookCache);
        mobile_book_handler::HistoryManager historyManager(sp_mongo_db, last_barter_handler, market_depth_handler);
        historyManager.replay();
        // websocket_cleanup();
    });

    cpp_app_launcher_thread.detach();
}

extern "C" void acquire_notify_semaphore() {
    // Wait for the semaphore to be released by cpp_app_launcher
    notify_semaphore.acquire();

}

extern "C" void release_notify_semaphore() {
    notify_semaphore.release();
}
