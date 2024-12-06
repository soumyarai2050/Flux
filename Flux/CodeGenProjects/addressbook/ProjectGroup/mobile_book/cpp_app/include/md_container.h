#pragma once

#include <iostream>
#include <array>

#include "../../../mobile_book/generated/CppUtilGen/mobile_book_service_shared_data_structure.h"
#include "../../../mobile_book/generated/CppUtilGen/mobile_book_constants.h"


constexpr auto MARKET_DEPTH_LEVEL = 10;

template<size_t N>
struct MDContainer {
    int64_t update_counter;
    char symbol_[mobile_book_handler::MAX_STRING_LENGTH];
    LastBarterQueueElement last_barter_;
    TopOfBookQueueElement top_of_book_;
    std::array<MarketDepthQueueElement, N> bid_market_depths_;
    std::array<MarketDepthQueueElement, N> ask_market_depths_;
};

