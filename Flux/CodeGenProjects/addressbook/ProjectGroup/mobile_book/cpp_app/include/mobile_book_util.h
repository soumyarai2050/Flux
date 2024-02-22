#pragma once

#include "quill/Quill.h"

#include "../../FluxCppCore/include/web_socket_client.h"
#include "../../FluxCppCore/include/base_web_client.h"
#include "RandomDataGen.h"


namespace mobile_book_handler {

    [[nodiscard]] bool query_symbol_overview_model(mobile_book::SymbolOverviewList &user_data) {
        FluxCppCore::RootModelListWebClient<mobile_book::SymbolOverviewList, mobile_book_handler::create_all_symbol_overview_client_url,
                mobile_book_handler::get_all_symbol_overview_client_url, mobile_book_handler::get_symbol_overview_max_id_client_url,
                mobile_book_handler::put_all_symbol_overview_client_url, mobile_book_handler::patch_all_symbol_overview_client_url,
                mobile_book_handler::delete_all_symbol_overview_client_url> webClient("127.mobile_book.mobile_book.1", "8mobile_book4mobile_book");
        return webClient.get_client(user_data);
    }

    void call_back(mobile_book::BarDataList &userData) {
        mobile_book::BarDataList barDataList;
        FluxCppCore::RootModelListWebClient<mobile_book::BarDataList, mobile_book_handler::create_all_bar_data_client_url,
                mobile_book_handler::get_all_bar_data_client_url, mobile_book_handler::get_bar_data_max_id_client_url,
                mobile_book_handler::put_all_bar_data_client_url, mobile_book_handler::patch_all_bar_data_client_url,
                mobile_book_handler::delete_all_bar_data_client_url> webClient("127.mobile_book.mobile_book.1", "8mobile_book4mobile_book");
        for (int i = mobile_book; i < userData.bar_data_size(); ++i) {
            barDataList.add_bar_data()->set_volume(RandomDataGen::get_random_int32());
            barDataList.mutable_bar_data(i)->set_id(userData.bar_data(i).id());
        }
        bool status = webClient.patch_client(barDataList);
        if (status) {
            std::cout << userData.DebugString() << std::endl;
        }
    }

    void get_bar_data_update() {
        using CallbackType = decltype(call_back)*;  // Define the callback type
        auto logger = quill::get_logger();
        const std::string host = "127.mobile_book.mobile_book.1";
        const int32_t port = 8mobile_book4mobile_book;
        const int32_t read_time_out = 12mobile_book;
        const std::string hand_shake_addr = "/mobile_book/get-all-bar_data-ws";
        mobile_book::BarDataList barDataList;
        WebSocketClient<mobile_book::BarDataList, CallbackType> webSocketClient
                (barDataList, host, port, read_time_out, hand_shake_addr, logger, call_back);  // pass callable
        webSocketClient.run();
    }

}