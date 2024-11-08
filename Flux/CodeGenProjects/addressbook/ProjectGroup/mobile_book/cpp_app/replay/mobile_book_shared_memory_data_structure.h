#pragma once

#include <iostream>
#include <array>
#include <mobile_book_service_shared_data_structure.h>


constexpr auto MARKET_DEPTH_LEVEL = 10;
constexpr auto MAX_STRING_LENGTH = 128;


struct MobileBookShmCache {
    int64_t update_counter;
    char symbol_[MAX_STRING_LENGTH];
    LastBarterQueueElement last_barter_;
    TopOfBookQueueElement top_of_book_;
    std::array<MarketDepthQueueElement, MARKET_DEPTH_LEVEL> bid_market_depths_;
    std::array<MarketDepthQueueElement, MARKET_DEPTH_LEVEL> ask_market_depths_;


    void print() const {
        std::cout << "Symbol: " << symbol_ << "\n";

        // Print Last Barter details
        std::cout << "\nLast Barter:\n";
        std::cout << "  Symbol: " << last_barter_.symbol_n_exch_id_.symbol_ << "\n";
        std::cout << "  Exchange ID: " << last_barter_.symbol_n_exch_id_.exch_id_ << "\n";
        std::cout << "  Exchange Time: " << last_barter_.exch_time_ << "\n";
        std::cout << "  Arrival Time: " << last_barter_.arrival_time_ << "\n";
        std::cout << "  Price: " << last_barter_.px_ << "\n";
        std::cout << "  Quantity: " << last_barter_.qty_ << "\n";
        std::cout << "  Premium: " << (last_barter_.is_premium_set_ ? std::to_string(last_barter_.premium_) : "Not Set") << "\n";
        std::cout << "  Market Barter Volume: " << (last_barter_.is_market_barter_volume_set_ ? "Set" : "Not Set") << "\n";

        // Print Top of Book details
        std::cout << "\nTop of Book:\n";
        std::cout << "  Symbol: " << top_of_book_.symbol_ << "\n";
        std::cout << "  Bid Quote:\n";
        std::cout << "    Price: " << top_of_book_.bid_quote_.px_ << (top_of_book_.is_bid_quote_set_ ? "" : " (Not Set)") << "\n";
        std::cout << "    Quantity: " << top_of_book_.bid_quote_.qty_ << (top_of_book_.is_bid_quote_set_ ? "" : " (Not Set)") << "\n";
        std::cout << "    Premium: " << (top_of_book_.bid_quote_.is_premium_set_ ? std::to_string(top_of_book_.bid_quote_.premium_) : "Not Set") << "\n";
        std::cout << "  Ask Quote:\n";
        std::cout << "    Price: " << top_of_book_.ask_quote_.px_ << (top_of_book_.is_ask_quote_set_ ? "" : " (Not Set)") << "\n";
        std::cout << "    Quantity: " << top_of_book_.ask_quote_.qty_ << (top_of_book_.is_ask_quote_set_ ? "" : " (Not Set)") << "\n";
        std::cout << "    Premium: " << (top_of_book_.ask_quote_.is_premium_set_ ? std::to_string(top_of_book_.ask_quote_.premium_) : "Not Set") << "\n";
        std::cout << "  Last Barter Quote:\n";
        std::cout << "    Price: " << top_of_book_.last_barter_.px_ << (top_of_book_.is_last_barter_set_ ? "" : " (Not Set)") << "\n";
        std::cout << "    Quantity: " << top_of_book_.last_barter_.qty_ << (top_of_book_.is_last_barter_set_ ? "" : " (Not Set)") << "\n";
        std::cout << "    Premium: " << (top_of_book_.last_barter_.is_premium_set_ ? std::to_string(top_of_book_.last_barter_.premium_) : "Not Set") << "\n";
        std::cout << "  Total Bartering Security Size: " << (top_of_book_.is_total_bartering_security_size_set_ ? std::to_string(top_of_book_.total_bartering_security_size_) : "Not Set") << "\n";
        std::cout << "  Last Update Date Time: " << (top_of_book_.is_last_update_date_time_set_ ? top_of_book_.last_update_date_time_ : "Not Set") << "\n";

        // Print Bid Market Depths
        std::cout << "\nBid Market Depths:\n";
        for (size_t i = 0; i < bid_market_depths_.size(); ++i) {
            const auto& depth = bid_market_depths_[i];
            std::cout << "  Level " << i + 1 << ":\n";
            std::cout << "    Price: " << depth.px_ << (depth.is_px_set_ ? "" : " (Not Set)") << "\n";
            std::cout << "    Quantity: " << depth.qty_ << (depth.is_qty_set_ ? "" : " (Not Set)") << "\n";
            std::cout << "    Position: " << depth.position_ << "\n";
            std::cout << "    Cumulative Notional: " << (depth.is_cumulative_notional_set_ ? std::to_string(depth.cumulative_notional_) : "Not Set") << "\n";
            std::cout << "    Cumulative Quantity: " << (depth.is_cumulative_qty_set_ ? std::to_string(depth.cumulative_qty_) : "Not Set") << "\n";
        }

        // Print Ask Market Depths
        std::cout << "\nAsk Market Depths:\n";
        for (size_t i = 0; i < ask_market_depths_.size(); ++i) {
            const auto& depth = ask_market_depths_[i];
            std::cout << "  Level " << i + 1 << ":\n";
            std::cout << "    Price: " << depth.px_ << (depth.is_px_set_ ? "" : " (Not Set)") << "\n";
            std::cout << "    Quantity: " << depth.qty_ << (depth.is_qty_set_ ? "" : " (Not Set)") << "\n";
            std::cout << "    Position: " << depth.position_ << "\n";
            std::cout << "    Cumulative Notional: " << (depth.is_cumulative_notional_set_ ? std::to_string(depth.cumulative_notional_) : "Not Set") << "\n";
            std::cout << "    Cumulative Quantity: " << (depth.is_cumulative_qty_set_ ? std::to_string(depth.cumulative_qty_) : "Not Set") << "\n";
        }

        std::cout << std::endl;
    }


};

struct ShmSymbolCache {
    MobileBookShmCache m_leg_1_data_shm_cache_;
    MobileBookShmCache m_leg_2_data_shm_cache_;

    [[nodiscard]] bool is_data_set() const {
        return m_leg_2_data_shm_cache_.update_counter != 0 || m_leg_1_data_shm_cache_.update_counter!= 0;
    }
};
