#pragma once

#include <ostream>
#include <chrono>
#include <string>
#include <utility>
#include "MD_Utils.h"

namespace md_handler {
    static const std::string key_delim = "_";

    class MD_DepthSingleSide{
    public:
        static std::string get_pos_symbol_side_key(const int8_t position, const std::string &symbol, const std::string &side){
            return std::to_string(position).
                    append(key_delim).
                    append(symbol).
                    append(key_delim).
                    append(side);
        }

        MD_DepthSingleSide(const int64_t qty_, const double px_, const int8_t position_, std::string symbol_,
                           std::string side_, int64_t cumulativeQty_ = 0, double cumulativeNotional_ = 0,
                           double cumulativeAvgPx_ = 0): qty(qty_), px(px_), position(position_), symbol(std::move(symbol_)),
                        side(std::move(side_)), cumulative_qty(cumulativeQty_), cumulative_notional(cumulativeNotional_),
                        cumulative_avg_px(cumulativeAvgPx_){
            position_symbol_side_key = get_pos_symbol_side_key(position, symbol, side);
            is_empty = false;
        }

        friend std::ostream &operator<<(std::ostream &os, const MD_DepthSingleSide &side) {
            os << "DepthSingleSide [qty: " << side.qty << " px: " << side.px << " position: " << side.position << " symbol: "
               << side.symbol << " side: " << side.side << " cumulative_qty: " << side.cumulative_qty << " premium: "
               << side.premium << " cumulative_notional: " << side.cumulative_notional << " cumulative_avg_px: "
               << side.cumulative_avg_px << " milliseconds_since_epoch: " << side.milliseconds_since_epoch
               << " position_symbol_side_key: " << side.position_symbol_side_key << " is_empty: " << side.is_empty << "]";
            return os;
        }

        MD_DepthSingleSide()=default;

        MD_DepthSingleSide(int8_t position_, std::string side_):position(position_), side(std::move(side_)){}

        void reset(){
            qty = 0;
            px = 0;
            symbol.clear();
            position_symbol_side_key.clear();
            cumulative_qty = 0;
            cumulative_notional = 0;
            cumulative_avg_px = 0;
            milliseconds_since_epoch = 0;
            is_empty = true;
        }

        [[nodiscard]] std::string get_position_symbol_side_key() {
            if (position_symbol_side_key.empty()) {
                position_symbol_side_key = get_pos_symbol_side_key(position, symbol, side);
            }
            return position_symbol_side_key;
        }

        void setQty(int64_t qty_) {
            is_empty = false;
            qty = qty_;
        }

        void setPx(double px_) {
            is_empty = false;
            px = px_;
        }

        void setSymbol(const std::string &symbol_) {
            MD_DepthSingleSide::symbol = symbol_;
        }

        void setPremium(double premium_) {
            is_empty = false;
            premium = premium_;
        }

        [[nodiscard]] double getPremium() const {
            return premium;
        }

        [[nodiscard]] int64_t getQty() const {
            return qty;
        }
        [[nodiscard]] double getPx() const {
            return px;
        }
        [[nodiscard]] int8_t getPosition() const {
            return position;
        }
        [[nodiscard]] std::string getSymbol() const {
            return symbol;
        }
        [[nodiscard]] std::string getSide() const {
            return side;
        }

        [[nodiscard]] int64_t getCumulativeQty() const {
            return cumulative_qty;
        }
        void setCumulativeQty(int64_t cumulativeQty) {
            cumulative_qty = cumulativeQty;
        }

        [[nodiscard]] double getCumulativeNotional() const {
            return cumulative_notional;
        }
        void setCumulativeNotional(double cumulativeNotional) {
            cumulative_notional = cumulativeNotional;
        }

        [[nodiscard]] double getCumulativeAvgPx() const {
            return cumulative_avg_px;
        }
        void setCumulativeAvgPx(double cumulativeAvgPx) {
            cumulative_avg_px = cumulativeAvgPx;
        }

        [[nodiscard]] int64_t getMillisecondsSinceEpoch() const {
            return milliseconds_since_epoch;
        }

        void setMillisecondsSinceEpoch(int64_t millisecondsSinceEpoch) {
            milliseconds_since_epoch = millisecondsSinceEpoch;
        }

        [[nodiscard]] bool isEmpty() const{
            return is_empty;
        }

    protected:
        int64_t qty = 0;
        double px = 0;
        int8_t position = -1;
        std::string symbol;
        std::string side;
        int64_t cumulative_qty = 0;
        double premium = 0;
        double cumulative_notional = 0;
        double cumulative_avg_px = 0;
        int64_t milliseconds_since_epoch{};

    private:
        std::string position_symbol_side_key;
        bool is_empty = true;
    };

    static MD_DepthSingleSide empty_market_depth_data{};
}

