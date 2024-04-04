#pragma once
#include <string>

namespace md_handler {

    class MD_LastBarter{
    public:
        explicit MD_LastBarter()= default;

        MD_LastBarter(const std::string &symbol_, const double px_, const int64_t qty_,
                     const int64_t milliseconds_since_epoch_ = 0, const std::string &exchange_ = "",
                     const std::string &special_conditions_ = "", const bool &past_limit_ = false,
                     const bool &unreported_ = false, const int64_t last_n_sec_total_qty_ = 0,
                     const int64_t applicable_period_seconds_ = 0):
                symbol(symbol_), px(px_), qty(qty_), milliseconds_since_epoch(milliseconds_since_epoch_), exchange(exchange_),
                special_conditions(special_conditions_), past_limit(past_limit_), unreported(unreported_),
                last_barter_qty_sum(last_n_sec_total_qty_), applicable_period_seconds(applicable_period_seconds_){}

        [[nodiscard]] int64_t getQty() const {
            return qty;
        }
        [[nodiscard]] double getPx() const {
            return px;
        }

        [[nodiscard]] int64_t getApplicablePeriodSeconds() const {
            return applicable_period_seconds;
        }

        [[nodiscard]] int64_t getLastBarterQtySum() const{
            return last_barter_qty_sum;
        }

        void setLastBarterQtySum(int64_t lastBarterQtySum) {
            last_barter_qty_sum = lastBarterQtySum;
        }

        [[nodiscard]] const std::string &getSymbol() const {
            return symbol;
        }

        [[nodiscard]] const std::string &getExchange() const {
            return exchange;
        }

        [[nodiscard]] const std::string &getSpecialConditions() const {
            return special_conditions;
        }

        [[nodiscard]] const bool &getPastLimit() const {
            return past_limit;
        }

        [[nodiscard]] const bool &getUnreported() const {
            return unreported;
        }

        [[nodiscard]] int64_t getMillisecondsSinceEpoch() const {
            return milliseconds_since_epoch;
        }

        void setMillisecondsSinceEpoch(int64_t millisecondsSinceEpoch) {
            milliseconds_since_epoch = millisecondsSinceEpoch;
        }

    protected:
        int64_t qty = 0;
        double px = 0;
        const std::string symbol;
        const std::string exchange;
        const std::string special_conditions;
        bool past_limit = false;
        bool unreported = false;
        int64_t last_barter_qty_sum = 0;
        int64_t applicable_period_seconds = 0;
        int64_t milliseconds_since_epoch = 0;

    private:
        std::string symbol_side_key;
    };

    class MD_MktOverview{
    public:
        [[nodiscard]] MD_LastBarter &getLastBarter() const {
            return last_barter;
        }
        [[nodiscard]] int64_t getTotalBarteringSecSize() const {
            return total_bartering_sec_size;
        }

        MD_MktOverview(MD_LastBarter &last_barter_, const long total_bartering_sec_size_)
        :last_barter(last_barter_), total_bartering_sec_size(total_bartering_sec_size_){}
    protected:
        MD_LastBarter &last_barter;
        int64_t total_bartering_sec_size;
    };
}



