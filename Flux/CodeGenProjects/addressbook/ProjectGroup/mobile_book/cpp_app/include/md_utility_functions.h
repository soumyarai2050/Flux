#pragma once

#include "shm_symbol_cache.h"
#include "utility_functions.h"

namespace mobile_book_handler {
    template<size_t N>
    inline void format_data(MDContainer<N> const& cache, std::vector<char>& buffer, const bool print_cumulative_fields = false) {

        std::format_to(std::back_inserter(buffer), "\n{:*^40}\n\n", std::string_view(cache.symbol_));
        std::format_to(std::back_inserter(buffer), "{:*^40}\n\n", "Last Barter");
        std::format_to(std::back_inserter(buffer), "SYMBOL      EXCH ID  PRICE      QTY    PREMIUM    EXCH TS          ARR TS\n");
        std::format_to(std::back_inserter(buffer), "{:<10}  {:<7}  {:<10.3f}  {:<6}  {:<8.3f}  {:<14}  {:<14}\n\n",
            std::string_view(cache.last_barter_.symbol_n_exch_id_.symbol_),
            std::string_view(cache.last_barter_.symbol_n_exch_id_.exch_id_),
            cache.last_barter_.px_,
            cache.last_barter_.qty_,
            cache.last_barter_.premium_,
            FluxCppCore::time_in_utc_str(cache.last_barter_.exch_time_),
            FluxCppCore::time_in_utc_str(cache.last_barter_.arrival_time_));

        const auto top_bid_qty = (int)cache.top_of_book_.bid_quote_.qty_;
        const auto top_bid_px = (float)cache.top_of_book_.bid_quote_.px_;

        const auto top_ask_qty = (int)cache.top_of_book_.ask_quote_.qty_;
        const auto top_ask_px = (float)cache.top_of_book_.ask_quote_.px_;

        const auto last_barter_qty = (int)cache.top_of_book_.last_barter_.qty_;
        const auto last_barter_px = (float)cache.top_of_book_.last_barter_.px_;

        std::format_to(std::back_inserter(buffer), "{:*^40}\n\n", "Top of Book");
        std::format_to(std::back_inserter(buffer), "BID QTY  BID PRICE  ASK QTY  ASK PRICE  LAST QTY  "
                                                   "LAST PRICE          TIME\n");
        std::format_to(std::back_inserter(buffer), "{:6}  {:10.3f}  {:6}  {:10.3f}  {:6}  {:10.3f}      {:<14}\n\n",
            top_bid_qty, top_bid_px, top_ask_qty, top_ask_px, last_barter_qty, last_barter_px,
            FluxCppCore::time_in_utc_str(cache.top_of_book_.last_update_date_time_));

        if (print_cumulative_fields) {
            constexpr auto md_format_spec = "{:10.3f}                   {:6}                    {:10.3f}                "
                                        "{:6}       {:10.3f}     {:10.3f}  {:6}       {:10.3f}                          "
                                        "{:6}                               {:10.3f}\n";
            // BUY CUM QTY , BUY CUM px , BUY QTY, BUY PX, SELL PX, SELL QTY, SELL CUM PX, SELL CUM QTY
            std::format_to(std::back_inserter(buffer), "{:*^40}\n", "Market Depth");
            std::format_to(std::back_inserter(buffer), "BUY CUMULATIVE NOTIONAL  BUY CUMULATIVE QTY"
                                                       "  BUY CUMULATIVE AVG PX  BUY QTY    BUY PX          SELL PX  SELL QTY  "
                                                       "SELL CUMULATIVE NOTIONAL  SELL CUMULATIVE QTY   "
                                                       "SELL CUMULATIVE AVG PX\n\n");
           for (size_t i{0}; i < MARKET_DEPTH_LEVEL; ++i) {
                const auto& bid = cache.bid_market_depths_[i];
                const auto& ask = cache.ask_market_depths_[i];
                auto bid_qty = bid.qty_ ;
                auto bid_px = bid.px_;

                auto ask_qty = ask.qty_;
                auto ask_px = ask.px_;

                std::format_to(std::back_inserter(buffer), md_format_spec,
                    bid.cumulative_notional_, bid.cumulative_qty_, bid.cumulative_avg_px_, bid_qty, bid_px,
                    ask_px, ask_qty, ask.cumulative_notional_, ask.cumulative_qty_, ask.cumulative_avg_px_);
            }
        } else {
            constexpr auto md_format_spec = "{:<14}                 {:<14}                 {:6}       {:10.3f}     "
                                            "{:10.3f}  {:6}         {:<14}                 {:<14}\n";
            // BUY CUM QTY , BUY CUM px , BUY QTY, BUY PX, SELL PX, SELL QTY, SELL CUM PX, SELL CUM QTY
            std::format_to(std::back_inserter(buffer), "{:*^40}\n", "Market Depth");
            std::format_to(std::back_inserter(buffer), "EXCH TS                ARR TS                "
                                                       "BUY QTY    BUY PX          SELL PX  SELL QTY       "
                                                       "EXCH TS                    ARR TS\n\n");
           for (size_t i{0}; i < MARKET_DEPTH_LEVEL; ++i) {
                const auto& bid = cache.bid_market_depths_[i];
                const auto& ask = cache.ask_market_depths_[i];
                auto bid_qty = bid.qty_ ;
                auto bid_px = bid.px_;

                auto ask_qty = ask.qty_;
                auto ask_px = ask.px_;

                std::format_to(std::back_inserter(buffer), md_format_spec,
                    FluxCppCore::time_in_utc_str(bid.exch_time_),
                    FluxCppCore::time_in_utc_str(bid.arrival_time_), bid_qty, bid_px, ask_px, ask_qty,
                    FluxCppCore::time_in_utc_str(ask.exch_time_), FluxCppCore::time_in_utc_str(ask.arrival_time_));
            }
        }

    }

    // Function to process MarketDepthQueueElement array
    inline void compute_cumulative_fields_from_market_depth_elements(
        std::array<MarketDepthQueueElement, MARKET_DEPTH_LEVEL>& elements, const char side, const std::string& symbol) {

        std::array<MarketDepthQueueElement, MARKET_DEPTH_LEVEL> filtered_elements = {};
        size_t filtered_count = 0;

        for (const auto& elem : elements) {
            if (elem.symbol_ == symbol && elem.side_ == side) {
                if (filtered_count < filtered_elements.size()) {
                    filtered_elements[filtered_count++] = elem;
                } else {
                    throw std::runtime_error("Filtered elements exceed maximum allowed size.");
                }
            }
        }

        if (filtered_count == 0) {
            throw std::runtime_error("No elements match the given side and symbol.");
        }

        std::sort(filtered_elements.begin(), filtered_elements.begin() + filtered_count,
                  [](const MarketDepthQueueElement& a, const MarketDepthQueueElement& b) {
                      return a.position_ < b.position_;
                  });

        double cumulative_notional = 0.0;
        int64_t cumulative_qty = 0;

        for (size_t i = 0; i < filtered_count; ++i) {
            auto& elem = filtered_elements[i];
            if (elem.is_px_set_ && elem.is_qty_set_) {
                double notional = elem.px_ * elem.qty_;
                cumulative_notional += notional;
                cumulative_qty += elem.qty_;

                elem.cumulative_notional_ = cumulative_notional;
                elem.is_cumulative_notional_set_ = true;

                elem.cumulative_qty_ = cumulative_qty;
                elem.is_cumulative_qty_set_ = true;

                elem.cumulative_avg_px_ = cumulative_qty > 0
                                               ? cumulative_notional / cumulative_qty
                                               : 0.0;
                elem.is_cumulative_avg_px_set_ = true;
            } else {
                elem.cumulative_notional_ = 0.0;
                elem.is_cumulative_notional_set_ = false;

                elem.cumulative_qty_ = 0;
                elem.is_cumulative_qty_set_ = false;

                elem.cumulative_avg_px_ = 0.0;
                elem.is_cumulative_avg_px_set_ = false;
            }
        }

        std::copy(filtered_elements.begin(), filtered_elements.begin() + filtered_count, elements.begin());
    }

    template<size_t N>
	std::string shm_snapshot(ShmSymbolCache<N> const& cache) {
		std::vector<char> buffer;
		format_data(cache.m_leg_1_data_shm_cache_, buffer);
		std::string data {buffer.begin(), buffer.end()};
		data += '\n';
		format_data(cache.m_leg_2_data_shm_cache_, buffer);
		data.append(buffer.begin(), buffer.end());
		return data;
	}

    template<size_t N>
    inline void compute_cumulative_fields_from_market_depth_elements(MDContainer<N>& r_container, const MarketDepthQueueElement& r_element) {
        // Select the relevant market depth array based on the side
        std::array<MarketDepthQueueElement, N>& md_array =
            (r_element.side_ == 'B') ? r_container.bid_market_depths_ : r_container.ask_market_depths_;

        auto position = r_element.position_;

        md_array[position] = r_element;

        // Initialize cumulative fields
        double cumulative_notional = 0.0;
        int64_t cumulative_qty = 0;

        // If there are preceding elements, use their cumulative values as the starting point
        if (position > 0) {
            const auto& prev_elem = md_array[position - 1];
            if (prev_elem.is_cumulative_notional_set_ && prev_elem.is_cumulative_qty_set_) {
                cumulative_notional = prev_elem.cumulative_notional_;
                cumulative_qty = prev_elem.cumulative_qty_;
            }
        }

        // Update cumulative fields starting from the current position
        for (size_t i = position; i < md_array.size(); ++i) {
            auto& elem = md_array[i];

            if (elem.is_px_set_ && elem.is_qty_set_) {
                double notional = elem.px_ * elem.qty_;
                cumulative_notional += notional;
                cumulative_qty += elem.qty_;

                elem.cumulative_notional_ = cumulative_notional;
                elem.is_cumulative_notional_set_ = true;

                elem.cumulative_qty_ = cumulative_qty;
                elem.is_cumulative_qty_set_ = true;

                elem.cumulative_avg_px_ = cumulative_qty > 0
                                               ? cumulative_notional / cumulative_qty
                                               : 0.0;
                elem.is_cumulative_avg_px_set_ = true;
            } else {
                if (r_element.side_ == 'B') {
                    r_container.bid_market_depths_ = md_array;
                } else {
                    r_container.ask_market_depths_ = md_array;
                }
                return;
            }
        }

    }


}