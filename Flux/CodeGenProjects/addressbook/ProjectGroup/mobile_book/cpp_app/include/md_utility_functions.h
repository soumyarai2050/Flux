#pragma once

namespace mobile_book_handler {
    inline void format_data(MDContainer const& cache, std::vector<char>& buffer) {

        std::format_to(std::back_inserter(buffer), "\n{:*^40}\n\n", std::string_view(cache.symbol_));

        std::format_to(std::back_inserter(buffer), "{:*^40}\n\n", "Last Barter");
        std::format_to(std::back_inserter(buffer), "SYMBOL      EXCH ID  PRICE      QTY    PREMIUM    EXCH TS          ARR TS\n");
        std::format_to(std::back_inserter(buffer), "{:<10}  {:<7}  {:<10.5f}  {:<6}  {:<8.2f}  {:<14}  {:<14}\n\n",
            std::string_view(cache.last_barter_.symbol_n_exch_id_.symbol_),
            std::string_view(cache.last_barter_.symbol_n_exch_id_.exch_id_),
            cache.last_barter_.px_,
            cache.last_barter_.qty_,
            cache.last_barter_.premium_,
            cache.last_barter_.exch_time_,
            cache.last_barter_.arrival_time_);

        const auto top_bid_qty = (int)cache.top_of_book_.bid_quote_.qty_;
        const auto top_bid_px = (float)cache.top_of_book_.bid_quote_.px_;

        const auto top_ask_qty = (int)cache.top_of_book_.ask_quote_.qty_;
        const auto top_ask_px = (float)cache.top_of_book_.ask_quote_.px_;

        const auto last_barter_qty = (int)cache.top_of_book_.last_barter_.qty_;
        const auto last_barter_px = (float)cache.top_of_book_.last_barter_.px_;

        std::format_to(std::back_inserter(buffer), "{:*^40}\n\n", "Top of Book");
        std::format_to(std::back_inserter(buffer), "BID QTY  BID PRICE  ASK QTY  ASK PRICE  LAST QTY  LAST PRICE\n");
        std::format_to(std::back_inserter(buffer), "{:6}  {:10.5f}  {:6}  {:10.5f}  {:6}  {:10.5f}\n\n",
            top_bid_qty, top_bid_px, top_ask_qty, top_ask_px, last_barter_qty, last_barter_px);

        std::format_to(std::back_inserter(buffer), "{:*^40}\n", "Market Depth");
        std::format_to(std::back_inserter(buffer), "BID QTY  BID PRICE  ASK QTY  ASK PRICE POSITION\n\n");
        for (size_t i{0}; i < MARKET_DEPTH_LEVEL; ++i) {
            const auto& bid = cache.bid_market_depths_[i];
            const auto& ask = cache.ask_market_depths_[i];
            auto bid_qty = bid.qty_ ;
            auto bid_px = bid.px_;

            auto ask_qty = ask.qty_;
            auto ask_px = ask.px_;

            std::format_to(std::back_inserter(buffer), "{:6}  {:10.5f}  {:6}  {:10.5f} {:6}\n",
                bid_qty, bid_px, ask_qty, ask_px, bid.position_);
        }

    }
}