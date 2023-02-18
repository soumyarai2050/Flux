#ifndef MD_HANDLER_MD_MARKETDEPTH_H
#define MD_HANDLER_MD_MARKETDEPTH_H

//#include "store_depth_market_data.h"

namespace md_handler {
    static const std::string key_delim = "_";

    class MD_MarketDepth{
    public:
        static std::string get_pos_symbol_side_key(const int8_t position, const std::string &symbol, const std::string &side){
            return std::to_string(position).
                    append(key_delim).
                    append(symbol).
                    append(key_delim).
                    append(side);
        }
        MD_MarketDepth(const int64_t qty_, const double px_, const int8_t position_, const std::string &symbol_,
                       const std::string &side_, int64_t cumulativeQty_ = 0, double cumulativeNotional_ = 0,
                       double cumulativeAvgPx_ = 0): qty(qty_), px(px_), position(position_), symbol(symbol_),
                        side(side_), cumulative_qty(cumulativeQty_), cumulative_notional(cumulativeNotional_),
                        cumulative_avg_px(cumulativeAvgPx_){
            position_symbol_side_key = get_pos_symbol_side_key(position, symbol, side);
            is_empty = false;
        }

        MD_MarketDepth()=default;

        [[nodiscard]] std::string get_position_symbol_side_key() const{
            return position_symbol_side_key;
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
        [[nodiscard]] const std::string &getSymbol() const {
            return symbol;
        }
        [[nodiscard]] const std::string &getSide() const {
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
        const std::string symbol;
        const std::string side;
        int64_t cumulative_qty = 0;
        double cumulative_notional = 0;
        double cumulative_avg_px = 0;
        int64_t milliseconds_since_epoch{};

    private:
        std::string position_symbol_side_key;
        bool is_empty = true;
    };

    static MD_MarketDepth empty_market_depth_data{};
}

#endif //MD_HANDLER_MD_MARKETDEPTH_H
