#include "last_trade_handler.h"
#include "market_depth_handler.h"
#include "history_manager.h"
#include "cpp_app_semaphore.h"
#include "mongo_db_singleton.h"
#include "mobile_book_service.pb.h"
#include "mock_mobile_book_cache.h"

int main() {

    std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db = MongoDBHandlerSingleton::get_instance();
    mobile_book_handler::MarketDepthHandler marketDepthHandler(sp_mongo_db);
    mobile_book_handler::LastTradeHandler lastTradeHandler(sp_mongo_db);
    mobile_book_handler::HistoryManager historyManager(sp_mongo_db, lastTradeHandler, marketDepthHandler);
    historyManager.replay();
    return mobile_book;
}


extern "C" void cpp_app_launcher() {

    std::thread cpp_app_launcher_thread([&] {
        std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db = MongoDBHandlerSingleton::get_instance();
        mobile_book_handler::MarketDepthHandler marketDepthHandler(sp_mongo_db);
        mobile_book_handler::LastTradeHandler lastTradeHandler(sp_mongo_db);
        mobile_book_handler::HistoryManager historyManager(sp_mongo_db, lastTradeHandler, marketDepthHandler);
        historyManager.replay();
    });

    std::cout << "Returning thread back to python from cpp" << std::endl;
    cpp_app_launcher_thread.detach();
}

extern "C" void acquire_notify_semaphore() {
    // Wait for the semaphore to be released by cpp_app_launcher
    notify_semaphore.acquire();

    std::cout << "Replay is done, continuing execution in Python." << std::endl;
}

extern "C" void release_notify_semaphore() {
    notify_semaphore.release();
    std::cout << "Release is done, giving control to Python" << std::endl;
}

