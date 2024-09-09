#pragma once

#include <chrono>
#include <atomic>

#include "mobile_book_service.pb.h"
#include "mobile_book_web_socket_server.h"
#include "utility_functions.h"

namespace mobile_book_handler {
    extern int32_t tob_ws_port;
    extern int32_t md_ws_port;
    extern int32_t lt_ws_port;
    extern mobile_book::TopOfBook top_of_book_obj;
    extern mobile_book::LastBarter last_barter_obj;
    extern mobile_book::MarketDepth market_depth_obj;
    extern const std::chrono::seconds TIME_OUT_CONNECTION;
    extern std::atomic<bool> shutdown_db_n_ws_thread;
    void signal_handler([[maybe_unused]] int signal);

    struct SymbolNExchId {
        std::string sym_;
        std::string exch_id_;
    };


    struct MarketBarterVolume {
        std::string market_barter_volume_id_;
        int64_t participation_period_last_barter_qty_sum_;
        int32_t applicable_period_seconds_;
    };

    struct LastBarter {
        int32_t _id;
        SymbolNExchId symbol_n_exch_id_;
        std::string  exch_time_;
        std::string arrival_time_;
        double px_;
        int64_t qty_;
        double premium_;
        MarketBarterVolume market_barter_volume_;
    };

    struct PySymbolNExchId {
        const char* symbol_;
        const char* exch_id_;
    };

    struct PyMarketBarterVolume {
        const char* market_barter_volume_id_;
        int64_t participation_period_last_barter_qty_sum_;
        int32_t applicable_period_seconds_;
    };

    struct PyLastBarter {
        PySymbolNExchId symbol_n_exch_id_;
        const char* exch_time_;
        const char* arrival_time_;
        double px_;
        int64_t qty_;
        double premium_;
        PyMarketBarterVolume market_barter_volume_;
    };

    struct MarketDepth {
        int32_t id_;
        std::string symbol_;
        std::string exch_time_;
        std::string arrival_time_;
        char side_;
        int32_t position_;
        double px_;
        int64_t qty_;
        std::string market_maker_;
        bool is_smart_depth_;
        double cumulative_notional_;
        int64_t cumulative_qty_;
        double cumulative_avg_px_;
    };

    struct PyMktDepth {
        const char* symbol_;
        const char* exch_time_;
        const char* arrival_time_;
        char side_;
        int32_t position_;
        double px_;
        int64_t qty_;
        const char* market_maker_;
        bool is_smart_depth_;
        double cumulative_notional_;
        int64_t cumulative_qty_;
        double cumulative_avg_px_;
    };

    using last_barter_fp_t = int(*)(PyLastBarter const*);


    using mkt_depth_fp_t = int(*)(PyMktDepth const*);

    extern last_barter_fp_t last_barter_fp;
    extern mkt_depth_fp_t mkt_depth_fp;

    extern "C" void register_last_barter_fp(last_barter_fp_t fcb);

    extern "C" void register_mkt_depth_fp(mkt_depth_fp_t mdfp);

    extern "C" void register_last_barter_and_mkt_depth_fp(last_barter_fp_t fcb, mkt_depth_fp_t mdfp);
}
