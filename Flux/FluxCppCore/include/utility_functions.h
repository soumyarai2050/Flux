#pragma once

#include <boost/asio.hpp>
#include <Python.h>
#include <quill/Quill.h>
#include <yaml-cpp/yaml.h>

#include "market_data_service.pb.h"
#include "market_data_constants.h"
#include "string_util.h"
#include "logger.h"

namespace FluxCppCore {

    inline int32_t find_free_port() {
        boost::asio::io_service io;
        boost::asio::ip::tcp::acceptor acceptor(io, boost::asio::ip::tcp::endpoint(boost::asio::ip::tcp::v4(), 0));
        return static_cast<int32_t>(acceptor.local_endpoint().port());
    }

    void inline get_trade_symbols_from_config(std::vector<std::string> &r_symbols_out) {
            const char* config_file = getenv("CONFIG_FILE");
            if (!config_file) {
                throw std::runtime_error("export env variable {CONFIG_FILE}");
            }
            if (access(config_file, F_OK) != 0) {
                throw std::runtime_error(std::format("{} not accessable", config_file));
            }

            YAML::Node config = YAML::LoadFile(config_file);
            r_symbols_out = config[market_data_handler::symbol_fld_name].as<std::vector<std::string>>();

        }

        int8_t inline get_market_depth_levels_from_config() {
            const char* config_file = getenv("CONFIG_FILE");
            int8_t market_depth_levels{0};
            if (!config_file) {
                throw std::runtime_error("export env variable {CONFIG_FILE}");
            }
            if (access(config_file, F_OK) != 0) {
                throw std::runtime_error(std::format("{} not accessable", config_file));
            }
            YAML::Node config = YAML::LoadFile(config_file);
            market_depth_levels = config["market_depth_levels"].as<int8_t>();
            return market_depth_levels;
        }

    struct PythonGIL
    {
        PythonGIL() : py_gil_{PyGILState_Ensure()} {}
        ~PythonGIL() {PyGILState_Release(py_gil_);
        }


        PyGILState_STATE py_gil_;

    };

    enum class CacheOperationResult {
        SUCCESS_DB_AND_CACHE_UPDATE = 0,
        LOCK_NOT_FOUND,
        DB_AND_CACHE_UPDATE_FAILED,
        ERROR_SYMBOL_NOT_FOUND,
        RECEIVED_OLD_TIMESTAMP,
        MUTEX_NOT_AVAILABLE_FOR_LOCK,
        MUTEX_NOT_AVAILABLE
    };



    struct MessageTypeToPythonArgs {

        static PyObject* message_type_to_python_args(const market_data::MarketDepth &kr_market_depth_obj) {
            PyObject* p_args = nullptr;
            std::string exch_time = format_time(kr_market_depth_obj.exch_time());
            std::string arrival_time = format_time(kr_market_depth_obj.exch_time());
            if (kr_market_depth_obj.side() == market_data::TickType::BID) {
                p_args = PyTuple_Pack(13, PyLong_FromLong(kr_market_depth_obj.id()),
                                PyUnicode_DecodeUTF8(kr_market_depth_obj.symbol().c_str(),
                                                     static_cast<Py_ssize_t>(kr_market_depth_obj.symbol().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(exch_time.c_str(),
                                                     static_cast<Py_ssize_t>(exch_time.size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(arrival_time.c_str(),
                                                     static_cast<Py_ssize_t>(arrival_time.size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8("BID", static_cast<Py_ssize_t>(std::string("BID").size()), nullptr),
                                PyLong_FromLong(kr_market_depth_obj.position()),
                                PyFloat_FromDouble(kr_market_depth_obj.px()),
                                PyLong_FromLong(kr_market_depth_obj.qty()),
                                PyUnicode_DecodeUTF8(kr_market_depth_obj.market_maker().c_str(),
                                                     static_cast<Py_ssize_t>(kr_market_depth_obj.market_maker().size()),
                                                     nullptr),
                                PyBool_FromLong(kr_market_depth_obj.is_smart_depth()),
                                PyFloat_FromDouble(kr_market_depth_obj.cumulative_notional()),
                                PyLong_FromLong(kr_market_depth_obj.cumulative_qty()),
                                PyFloat_FromDouble(kr_market_depth_obj.cumulative_avg_px()));
            } else {
                p_args = PyTuple_Pack(13, PyLong_FromLong(kr_market_depth_obj.id()),
                                PyUnicode_DecodeUTF8(kr_market_depth_obj.symbol().c_str(),
                                                     static_cast<Py_ssize_t>(kr_market_depth_obj.symbol().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(exch_time.c_str(),
                                                     static_cast<Py_ssize_t>(exch_time.size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(arrival_time.c_str(),
                                                     static_cast<Py_ssize_t>(arrival_time.size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8("ASK", static_cast<Py_ssize_t>(std::string("ASk").size()), nullptr),
                                PyLong_FromLong(kr_market_depth_obj.position()),
                                PyFloat_FromDouble(kr_market_depth_obj.px()),
                                PyLong_FromLong(kr_market_depth_obj.qty()),
                                PyUnicode_DecodeUTF8(kr_market_depth_obj.market_maker().c_str(),
                                                     static_cast<Py_ssize_t>(kr_market_depth_obj.market_maker().size()),
                                                     nullptr),
                                PyBool_FromLong(kr_market_depth_obj.is_smart_depth()),
                                PyFloat_FromDouble(kr_market_depth_obj.cumulative_notional()),
                                PyLong_FromLong(kr_market_depth_obj.cumulative_qty()),
                                PyFloat_FromDouble(kr_market_depth_obj.cumulative_avg_px()));
            }
            return p_args;
        }

        static PyObject* message_type_to_python_args(const market_data::LastTrade &kr_last_trade_obj, PyObject* p_market_trade_volume) {
            std::string exch_time = format_time(kr_last_trade_obj.exch_time());
            std::string arrival_time = format_time(kr_last_trade_obj.exch_time());
            return PyTuple_Pack(9, PyLong_FromLong(kr_last_trade_obj.id()),
                                PyUnicode_DecodeUTF8(kr_last_trade_obj.symbol_n_exch_id().symbol().c_str(),
                                                     static_cast<Py_ssize_t>(kr_last_trade_obj.symbol_n_exch_id().symbol().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(kr_last_trade_obj.symbol_n_exch_id().exch_id().c_str(),
                                                     static_cast<Py_ssize_t>(kr_last_trade_obj.symbol_n_exch_id().exch_id().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(exch_time.c_str(),
                                                     static_cast<Py_ssize_t>(exch_time.size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(arrival_time.c_str(),
                                                     static_cast<Py_ssize_t>(arrival_time.size()),
                                                     nullptr),
                                PyFloat_FromDouble(kr_last_trade_obj.px()),
                                PyLong_FromLong(kr_last_trade_obj.qty()),
                                PyFloat_FromDouble(kr_last_trade_obj.premium()),
                                p_market_trade_volume);
        }

        static PyObject* message_type_to_python_args(const market_data::TopOfBook &kr_top_of_book_obj, PyObject* p_market_trade_volume) {
            PyObject* p_args = nullptr;
            std::string last_update_date_time = format_time(kr_top_of_book_obj.last_update_date_time());
            if (kr_top_of_book_obj.has_bid_quote()) {
                std::string bid_quote_last_update_date_time = format_time(kr_top_of_book_obj.bid_quote().last_update_date_time());
                LOG_INFO_IMPL(GetLogger(), "Bid Quote: {}, total_trading_security_size: {}",
                    kr_top_of_book_obj.bid_quote().DebugString(), kr_top_of_book_obj.total_trading_security_size());
                p_args = PyTuple_Pack(17, PyLong_FromLong(kr_top_of_book_obj.id()),
                            PyUnicode_DecodeUTF8(kr_top_of_book_obj.symbol().c_str(),
                                static_cast<Py_ssize_t>(kr_top_of_book_obj.symbol().size()), nullptr),
                            PyFloat_FromDouble(kr_top_of_book_obj.bid_quote().px()),
                            PyLong_FromLong(kr_top_of_book_obj.bid_quote().qty()),
                            PyFloat_FromDouble(kr_top_of_book_obj.bid_quote().premium()),
                            Py_None, Py_None, Py_None, Py_None, Py_None, Py_None,
                            PyUnicode_DecodeUTF8(bid_quote_last_update_date_time.c_str(),
                                static_cast<Py_ssize_t>(bid_quote_last_update_date_time.size()),
                                nullptr),
                            Py_None, Py_None,
                            kr_top_of_book_obj.has_total_trading_security_size() ? Py_None : PyLong_FromLong(
                                kr_top_of_book_obj.total_trading_security_size()),
                            Py_None,
                            PyUnicode_DecodeUTF8(last_update_date_time.c_str(),
                                static_cast<Py_ssize_t>(last_update_date_time.size()), nullptr));
            }

            if (kr_top_of_book_obj.has_ask_quote()) {
                std::string ask_quote_last_update_date_time = format_time(kr_top_of_book_obj.ask_quote().last_update_date_time());
                LOG_INFO_IMPL(GetLogger(), "Ask Quote: {}, total_trading_security_size: {}",
                    kr_top_of_book_obj.ask_quote().DebugString(), kr_top_of_book_obj.total_trading_security_size());
                p_args = PyTuple_Pack(17, PyLong_FromLong(kr_top_of_book_obj.id()),
                            PyUnicode_DecodeUTF8(kr_top_of_book_obj.symbol().c_str(),
                                static_cast<Py_ssize_t>(kr_top_of_book_obj.symbol().size()), nullptr),
                            Py_None, Py_None, Py_None,
                            PyFloat_FromDouble(kr_top_of_book_obj.ask_quote().px()),
                            PyLong_FromLong(kr_top_of_book_obj.ask_quote().qty()),
                            PyFloat_FromDouble(kr_top_of_book_obj.ask_quote().premium()),
                            Py_None, Py_None, Py_None, Py_None,
                            PyUnicode_DecodeUTF8(ask_quote_last_update_date_time.c_str(),
                                static_cast<Py_ssize_t>(ask_quote_last_update_date_time.size()),
                                nullptr),
                            Py_None,
                            kr_top_of_book_obj.has_total_trading_security_size() ? Py_None : PyLong_FromLong(
                                kr_top_of_book_obj.total_trading_security_size()),
                            Py_None,
                            PyUnicode_DecodeUTF8(last_update_date_time.c_str(),
                                static_cast<Py_ssize_t>(last_update_date_time.size()), nullptr));
            }

            if (kr_top_of_book_obj.has_last_trade()) {
                std::string last_trade_last_update_date_time = format_time(kr_top_of_book_obj.last_trade().last_update_date_time());
                LOG_INFO_IMPL(GetLogger(), "Last Trade: {}, total_trading_security_size: {}",
                    kr_top_of_book_obj.ask_quote().DebugString(), kr_top_of_book_obj.total_trading_security_size());
                p_args = PyTuple_Pack(17, PyLong_FromLong(kr_top_of_book_obj.id()),
                            PyUnicode_DecodeUTF8(kr_top_of_book_obj.symbol().c_str(),
                                static_cast<Py_ssize_t>(kr_top_of_book_obj.symbol().size()), nullptr),
                            Py_None, Py_None, Py_None, Py_None, Py_None, Py_None,
                            PyFloat_FromDouble(kr_top_of_book_obj.last_trade().px()),
                            PyLong_FromLong(kr_top_of_book_obj.last_trade().qty()),
                            PyFloat_FromDouble(kr_top_of_book_obj.last_trade().premium()),
                            Py_None, Py_None,
                            PyUnicode_DecodeUTF8(last_trade_last_update_date_time.c_str(),
                                static_cast<Py_ssize_t>(last_trade_last_update_date_time.size()),
                                nullptr),
                            kr_top_of_book_obj.has_total_trading_security_size() ? Py_None : PyLong_FromLong(
                                kr_top_of_book_obj.total_trading_security_size()),
                            p_market_trade_volume,
                            PyUnicode_DecodeUTF8(last_update_date_time.c_str(),
                                static_cast<Py_ssize_t>(last_update_date_time.size()), nullptr));
            }

            return p_args;

        }

        static PyObject* message_type_to_python_args(const market_data::MarketTradeVolume &kr_market_trade_volume_obj) {
            return PyTuple_Pack(3, PyUnicode_DecodeUTF8(kr_market_trade_volume_obj.id().c_str(),
                                                        static_cast<Py_ssize_t>(kr_market_trade_volume_obj.id().size()),
                                                        nullptr),
                                PyLong_FromLong(kr_market_trade_volume_obj.participation_period_last_trade_qty_sum()),
                                PyLong_FromLong(kr_market_trade_volume_obj.applicable_period_seconds()));
        }

        static PyObject* message_type_to_python_args(const market_data::Quote &kr_quote_obj) {
            std::string quote_last_update_date_time = format_time(kr_quote_obj.last_update_date_time());
            return PyTuple_Pack(4, PyFloat_FromDouble(kr_quote_obj.px()),
                                PyLong_FromLong(kr_quote_obj.qty()),
                                PyFloat_FromDouble(kr_quote_obj.premium()),
                                PyUnicode_DecodeUTF8(quote_last_update_date_time.c_str(),
                                                     static_cast<Py_ssize_t>(quote_last_update_date_time.size()),
                                                     nullptr));
        }
    };



}