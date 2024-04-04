#pragma once

#include <boost/asio.hpp>

namespace FluxCppCore {

    int32_t find_free_port() {
        boost::asio::io_service io;
        boost::asio::ip::tcp::acceptor acceptor(io, boost::asio::ip::tcp::endpoint(boost::asio::ip::tcp::v4(), 0));
        return static_cast<int32_t>(acceptor.local_endpoint().port());
    }

    struct PythonGIL
    {
        PythonGIL() : py_gil_{PyGILState_Ensure()} {}
        ~PythonGIL() {PyGILState_Release(py_gil_);
        }


        PyGILState_STATE py_gil_;

    };

    struct MessageTypeToPythonArgs {

        static PyObject* message_type_to_python_args(const market_data::MarketDepth &kr_market_depth_obj) {
            return PyTuple_Pack(13, PyLong_FromLong(kr_market_depth_obj.id()),
                                PyUnicode_DecodeUTF8(kr_market_depth_obj.symbol().c_str(),
                                                     static_cast<Py_ssize_t>(kr_market_depth_obj.symbol().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(kr_market_depth_obj.exch_time().c_str(),
                                                     static_cast<Py_ssize_t>(kr_market_depth_obj.exch_time().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(kr_market_depth_obj.arrival_time().c_str(),
                                                     static_cast<Py_ssize_t>(kr_market_depth_obj.arrival_time().size()),
                                                     nullptr),
                                PyLong_FromLong(kr_market_depth_obj.side()),
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

        static PyObject* message_type_to_python_args(const market_data::LastTrade &kr_last_trade_obj, PyObject* p_market_trade_volume) {
            return PyTuple_Pack(9, PyLong_FromLong(kr_last_trade_obj.id()),
                                PyUnicode_DecodeUTF8(kr_last_trade_obj.symbol_n_exch_id().symbol().c_str(),
                                                     static_cast<Py_ssize_t>(kr_last_trade_obj.symbol_n_exch_id().symbol().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(kr_last_trade_obj.symbol_n_exch_id().exch_id().c_str(),
                                                     static_cast<Py_ssize_t>(kr_last_trade_obj.symbol_n_exch_id().exch_id().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(kr_last_trade_obj.exch_time().c_str(),
                                                     static_cast<Py_ssize_t>(kr_last_trade_obj.exch_time().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(kr_last_trade_obj.arrival_time().c_str(),
                                                     static_cast<Py_ssize_t>(kr_last_trade_obj.arrival_time().size()),
                                                     nullptr),
                                PyFloat_FromDouble(kr_last_trade_obj.px()),
                                PyLong_FromLong(kr_last_trade_obj.qty()),
                                PyFloat_FromDouble(kr_last_trade_obj.premium()),
                                p_market_trade_volume);
        }

        static PyObject* message_type_to_python_args(const market_data::TopOfBook &kr_top_of_book_obj, PyObject* p_market_trade_volume) {
            return PyTuple_Pack(17, PyLong_FromLong(kr_top_of_book_obj.id()),
                                PyUnicode_DecodeUTF8(kr_top_of_book_obj.symbol().c_str(),
                                                     static_cast<Py_ssize_t>(kr_top_of_book_obj.symbol().size()),
                                                     nullptr),
                                PyFloat_FromDouble(kr_top_of_book_obj.bid_quote().px()),
                                PyLong_FromLong(kr_top_of_book_obj.bid_quote().qty()),
                                PyFloat_FromDouble(kr_top_of_book_obj.bid_quote().premium()),
                                PyFloat_FromDouble(kr_top_of_book_obj.ask_quote().px()),
                                PyLong_FromLong(kr_top_of_book_obj.ask_quote().qty()),
                                PyFloat_FromDouble(kr_top_of_book_obj.ask_quote().premium()),
                                PyFloat_FromDouble(kr_top_of_book_obj.last_trade().px()),
                                PyLong_FromLong(kr_top_of_book_obj.last_trade().qty()),
                                PyFloat_FromDouble(kr_top_of_book_obj.last_trade().premium()),
                                PyUnicode_DecodeUTF8(kr_top_of_book_obj.bid_quote().last_update_date_time().c_str(),
                                                     static_cast<Py_ssize_t>(kr_top_of_book_obj.bid_quote().last_update_date_time().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(kr_top_of_book_obj.ask_quote().last_update_date_time().c_str(),
                                                     static_cast<Py_ssize_t>(kr_top_of_book_obj.ask_quote().last_update_date_time().size()),
                                                     nullptr),
                                PyUnicode_DecodeUTF8(kr_top_of_book_obj.last_trade().last_update_date_time().c_str(),
                                                     static_cast<Py_ssize_t>(kr_top_of_book_obj.last_trade().last_update_date_time().size()),
                                                     nullptr),
                                PyLong_FromLong(kr_top_of_book_obj.total_trading_security_size()),
                                p_market_trade_volume,
                                PyUnicode_DecodeUTF8(kr_top_of_book_obj.last_update_date_time().c_str(),
                                                     static_cast<Py_ssize_t>(kr_top_of_book_obj.last_update_date_time().size()),
                                                     nullptr));
        }

        static PyObject* message_type_to_python_args(const market_data::MarketTradeVolume &kr_market_trade_volume_obj) {
            return PyTuple_Pack(3, PyUnicode_DecodeUTF8(kr_market_trade_volume_obj.id().c_str(),
                                                        static_cast<Py_ssize_t>(kr_market_trade_volume_obj.id().size()),
                                                        nullptr),
                                PyLong_FromLong(kr_market_trade_volume_obj.participation_period_last_trade_qty_sum()),
                                PyLong_FromLong(kr_market_trade_volume_obj.applicable_period_seconds()));
        }

        static PyObject* message_type_to_python_args(const market_data::Quote &kr_quote_obj) {
            return PyTuple_Pack(4, PyFloat_FromDouble(kr_quote_obj.px()),
                                PyLong_FromLong(kr_quote_obj.qty()),
                                PyFloat_FromDouble(kr_quote_obj.premium()),
                                PyUnicode_DecodeUTF8(kr_quote_obj.last_update_date_time().c_str(),
                                                     static_cast<Py_ssize_t>(kr_quote_obj.last_update_date_time().size()),
                                                     nullptr));
        }
    };

    struct AddOrGetContainerObj {

        static void add_container_obj_for_symbol(const std::string &kr_symbol) {
            static PyObject* p_module = nullptr;
            static PyObject* p_add_container_obj_for_symbol_func_ = nullptr;
            PyObject* p_args = nullptr;

            p_module = PyImport_ImportModule(market_data_handler::market_data_cache_module_name.c_str());
            assert(p_module != nullptr && "Failed to import module");

            p_add_container_obj_for_symbol_func_ = PyObject_GetAttrString(p_module, market_data_handler::add_container_obj_for_symbol_key.c_str());
            p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_symbol.c_str(), static_cast<Py_ssize_t>(kr_symbol.size()), nullptr));
            PyObject_CallObject(p_add_container_obj_for_symbol_func_, p_args);
        }

        static PyObject* get_market_data_container_instance(const std::string &kr_symbol) {
            static PyObject* p_market_data_container_class = nullptr;
            PyObject* p_market_data_container_instance = nullptr;
            PyObject* p_args = nullptr;
            static PyObject* mp_module_ = nullptr;
            // TODO: avoid calling PyImport_ImportModule multiple times make member variable
            mp_module_ = PyImport_ImportModule(market_data_handler::market_data_cache_module_name.c_str());

            // TODO: avoid calling PyObject_GetAttrString multiple times make member variable
            p_market_data_container_class = PyObject_GetAttrString(mp_module_, market_data_handler::get_market_data_container_key.c_str());
            assert(p_market_data_container_class != nullptr);

            p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_symbol.c_str(), static_cast<Py_ssize_t>(kr_symbol.size()), nullptr));
            p_market_data_container_instance = PyObject_CallObject(p_market_data_container_class, p_args);
            if (p_market_data_container_instance == Py_None) {
                return nullptr;
            } else {
                return p_market_data_container_instance;
            }
        }

    };


}