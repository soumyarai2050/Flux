#include "history_manager.h"
#include "mongo_db_singleton.h"
#include "mobile_book_web_socket_server.h"
#include "mock_mobile_book_cache.h"

int main() {

    Py_Initialize();

    std::signal(SIGTERM, signal_handler);
    std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db = MongoDBHandlerSingleton::get_instance();
    mobile_book::TopOfBook top_of_book;
    mobile_book::MarketDepth market_depth;
    mobile_book::LastBarter last_barter;

    std::chrono::seconds ws_timeout = std::chrono::seconds(60);
    mobile_book_handler::MobileBookLastBarterWebSocketServer<mobile_book::LastBarter> lt_websocket_server_(last_barter, mobile_book_handler::host, FluxCppCore::find_free_port(), ws_timeout);
    mobile_book_handler::MobileBookMarketDepthWebSocketServer<mobile_book::MarketDepth> md_websocket_server_(market_depth, mobile_book_handler::host, FluxCppCore::find_free_port(), ws_timeout);
    mobile_book_handler::MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook> tob_websocket_server_(top_of_book, mobile_book_handler::host, FluxCppCore::find_free_port(), ws_timeout);

    std::thread top_of_book_websocket_thread_([&](){tob_websocket_server_.run();});
    std::thread last_barter_websocket_thread_([&](){lt_websocket_server_.run();});
    std::thread market_depth_websocket_thread_([&](){md_websocket_server_.run();});

    MobileBookInterface* mobile_book_interface = new MobileBookConsumer(
        sp_mongo_db, tob_websocket_server_, lt_websocket_server_, md_websocket_server_);
    mobile_book_interface->go();

    top_of_book_websocket_thread_.join();
    last_barter_websocket_thread_.join();
    market_depth_websocket_thread_.join();
    return 0;
}
