#pragma once

#include <iostream>
#include <mutex>
#include <Python.h>
#include <semaphore>

#include "mobile_book_service.pb.h"

namespace
{
    struct PythonGIL
    {
        PythonGIL() : py_gil_{PyGILState_Ensure()} {}
        ~PythonGIL() {PyGILState_Release(py_gil_);
            std::cout << "Released GIL\n";
        }


        PyGILState_STATE py_gil_;

    };
}

extern "C" void lock_mutex(PyObject* p_mutex_ptr) {

    assert(p_mutex_ptr != nullptr && "mutex pointer never be null");
    void* mutex_void_ptr = PyLong_AsVoidPtr(p_mutex_ptr);

    assert(mutex_void_ptr != nullptr && "Failed to convert into void ptr");

    std::mutex* std_mutex_ptr = static_cast<std::mutex*>(mutex_void_ptr);
    std_mutex_ptr->lock();


}


extern "C" void unlock_mutex(PyObject* p_mutex_ptr) {
    assert(p_mutex_ptr != nullptr);

    void* mutex_void_ptr = PyLong_AsVoidPtr(p_mutex_ptr);
    assert(mutex_void_ptr != nullptr);

    // Cast the pointer to std::mutex* type
    std::mutex* std_mutex_ptr = static_cast<std::mutex*>(mutex_void_ptr);
    std_mutex_ptr->unlock();

}


extern "C" PyObject* get_mobile_book_container_instance(const std::string &kr_symbol) {

    PyObject* p_module = nullptr;
    PyObject* p_market_depth_class_container_class = nullptr;
    PyObject* p_market_depth_class_container_instance = nullptr;
    PyObject* p_args = nullptr;

    p_module = PyImport_ImportModule("mobile_book_cache");
    assert(p_module != nullptr);

    p_market_depth_class_container_class = PyObject_GetAttrString(p_module, "get_mobile_book_container");
    assert(p_market_depth_class_container_class != nullptr);

    p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_symbol.c_str(), static_cast<Py_ssize_t>(kr_symbol.size()),
                                                 nullptr));
    p_market_depth_class_container_instance = PyObject_CallObject(p_market_depth_class_container_class, p_args);
    if (p_market_depth_class_container_instance == Py_None) {
        return nullptr;
    } else {
        return p_market_depth_class_container_instance;
    }
}

extern "C" PyObject* set_market_trade_volume(PyObject* p_mobile_book_container_instance,
                                             const mobile_book::MarketTradeVolume &kr_market_trade_volume_obj) {
    PyObject* p_set_func = nullptr;
    PyObject* p_args = nullptr;

    p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_market_trade_volume");
    assert(p_set_func != nullptr);

    p_args = PyTuple_Pack(3, PyUnicode_DecodeUTF8(kr_market_trade_volume_obj.id().c_str(),
                                                  static_cast<Py_ssize_t>(kr_market_trade_volume_obj.id().size()),
                                                  nullptr),
                          PyLong_FromLong(kr_market_trade_volume_obj.participation_period_last_trade_qty_sum()),
                          PyLong_FromLong(kr_market_trade_volume_obj.applicable_period_seconds()));
    return PyObject_CallObject(p_set_func, p_args);
}

extern "C" void create_top_of_book_cache(const mobile_book::TopOfBook &kr_top_of_book, PyObject* p_module,
                                         PyObject* p_mobile_book_container_instance) {
    PyObject* p_set_func = nullptr;
    PyObject* p_market_trade_volume_class = nullptr;
    PyObject* p_market_trade_volume_list = nullptr;
    PyObject* p_args = nullptr;
    PyObject* p_market_trade_volume_instance = nullptr;

    p_market_trade_volume_class = PyObject_GetAttrString(p_module, "MarketTradeVolume");
    p_market_trade_volume_list = PyList_New(0);
    p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book");
    for (int i = 0; i < kr_top_of_book.market_trade_volume_size(); ++i) {
        p_args = PyTuple_Pack(3, PyUnicode_DecodeUTF8(kr_top_of_book.market_trade_volume(i).id().c_str(),
                                                      static_cast<Py_ssize_t>(kr_top_of_book.market_trade_volume(
                                                              i).id().size()), nullptr),
                              PyLong_FromLong(kr_top_of_book.market_trade_volume(i).participation_period_last_trade_qty_sum()),
                              PyLong_FromLong(kr_top_of_book.market_trade_volume(i).applicable_period_seconds()));
        p_market_trade_volume_instance = PyObject_CallObject(p_market_trade_volume_class, p_args);
        assert(p_market_trade_volume_instance != nullptr);
        PyList_Append(p_market_trade_volume_list, p_market_trade_volume_instance);
    }
    p_args = PyTuple_Pack(17, PyLong_FromLong(kr_top_of_book.id()),
                          PyUnicode_DecodeUTF8(kr_top_of_book.symbol().c_str(),
                                               static_cast<Py_ssize_t>(kr_top_of_book.symbol().size()),
                                               nullptr),
                          PyFloat_FromDouble(kr_top_of_book.bid_quote().px()),
                          PyLong_FromLong(kr_top_of_book.bid_quote().qty()),
                          PyFloat_FromDouble(kr_top_of_book.bid_quote().premium()),
                          PyFloat_FromDouble(kr_top_of_book.ask_quote().px()),
                          PyLong_FromLong(kr_top_of_book.ask_quote().qty()),
                          PyFloat_FromDouble(kr_top_of_book.ask_quote().premium()),
                          PyFloat_FromDouble(kr_top_of_book.last_trade().px()),
                          PyLong_FromLong(kr_top_of_book.last_trade().qty()),
                          PyFloat_FromDouble(kr_top_of_book.last_trade().premium()),
                          PyUnicode_DecodeUTF8(kr_top_of_book.bid_quote().last_update_date_time().c_str(),
                                               static_cast<Py_ssize_t>(kr_top_of_book.bid_quote().last_update_date_time().size()),
                                               nullptr),
                          PyUnicode_DecodeUTF8(kr_top_of_book.ask_quote().last_update_date_time().c_str(),
                                               static_cast<Py_ssize_t>(kr_top_of_book.ask_quote().last_update_date_time().size()),
                                               nullptr),
                          PyUnicode_DecodeUTF8(kr_top_of_book.last_trade().last_update_date_time().c_str(),
                                               static_cast<Py_ssize_t>(kr_top_of_book.last_trade().last_update_date_time().size()),
                                               nullptr),
                          PyLong_FromLong(kr_top_of_book.total_trading_security_size()),
                          p_market_trade_volume_list,
                          PyUnicode_DecodeUTF8(kr_top_of_book.last_update_date_time().c_str(),
                                               static_cast<Py_ssize_t>(kr_top_of_book.last_update_date_time().size()),
                                               nullptr));

    PyObject_CallObject(p_set_func, p_args);
}

//std::unordered_map<std::string, std::vector<PyObject*>>
extern "C" bool update_or_create_top_of_book_cache(const mobile_book::TopOfBook &kr_top_of_book, const std::string &kr_side) {
    std::cout << "Patch top of book" << kr_side << "\n";
    Py_Initialize();

    PyObject* p_mobile_book_container_instance = nullptr;
    PyObject* p_module = nullptr;
    PyObject* p_set_func = nullptr;
    PyObject* p_args = nullptr;
    PyObject* p_result = nullptr;
    PyObject* p_market_trade_volume_class = nullptr;
    PyObject* p_market_trade_volume_instance = nullptr;
    PyObject* p_market_trade_volume_list = nullptr;
    PyObject* p_top_of_book_instance = nullptr;
    PyObject* p_mutex = nullptr;


    {
        ::PythonGIL gil;
        p_module = PyImport_ImportModule("mobile_book_cache");
        assert(p_module != nullptr);

        p_mobile_book_container_instance = get_mobile_book_container_instance(kr_top_of_book.symbol());

        std::cout << "Creating new container instance for symbol: " << kr_top_of_book.symbol() << std::endl;
        if (!p_mobile_book_container_instance) {
            p_set_func = PyObject_GetAttrString(p_module, "add_container_obj_for_symbol");
            PyObject_CallObject(p_set_func,
                                PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_top_of_book.symbol().c_str(),
                                                                     static_cast<Py_ssize_t>(kr_top_of_book.symbol().size()),
                                                                     nullptr)));
            p_mobile_book_container_instance = get_mobile_book_container_instance(kr_top_of_book.symbol());

            create_top_of_book_cache(kr_top_of_book, p_module, p_mobile_book_container_instance);
        } else {

            std::cout << "Using existing container instance for symbol: " << kr_top_of_book.symbol() << std::endl;
            PyObject* p_top_of_book_total_trading_security_size = PyObject_GetAttrString(p_mobile_book_container_instance,
                                                                                         "set_top_of_book_total_trading_security_size");
            PyObject* p_set_top_of_book_mkt_trade_vol_participation_period_last_trade_qty_sum =
                    PyObject_GetAttrString(p_mobile_book_container_instance,
                                           "set_top_of_book_market_trade_volume_participation_period_last_trade_qty_sum");
            PyObject* p_set_top_of_book_mkt_trade_vol_applicable_per_seconds =
                    PyObject_GetAttrString(p_mobile_book_container_instance,
                                           "set_top_of_book_market_trade_volume_applicable_period_seconds");
            PyObject* p_set_top_of_book_last_update_date_time = PyObject_GetAttrString(p_mobile_book_container_instance,
                                                                                       "set_top_of_book_last_update_date_time");

            assert(p_top_of_book_total_trading_security_size != nullptr &&
            p_set_top_of_book_mkt_trade_vol_participation_period_last_trade_qty_sum != nullptr &&
            p_set_top_of_book_mkt_trade_vol_applicable_per_seconds != nullptr &&
            p_set_top_of_book_last_update_date_time != nullptr);

            p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "get_top_of_book");
            p_top_of_book_instance = PyObject_CallObject(p_set_func, nullptr);

            if (p_top_of_book_instance == Py_None) {
                create_top_of_book_cache(kr_top_of_book, p_module, p_mobile_book_container_instance);
            } else {
                p_set_func = PyObject_GetAttrString(p_top_of_book_instance, "get_mutex");
                p_mutex = PyObject_CallObject(p_set_func, nullptr);
                void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
                std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);
                std::cout << "Got mutex\n";

                if (kr_side == "BID") {

                    PyObject* p_set_top_of_book_price = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_bid_quote_px");
                    PyObject* p_set_top_of_book_qty = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_bid_quote_qty");
                    PyObject* p_set_top_of_book_premium = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_bid_quote_premium");
                    PyObject* p_set_top_of_book_bid_quote_last_update_date_time =
                            PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_bid_quote_last_update_date_time");

                    assert(p_set_top_of_book_price != nullptr and
                    p_set_top_of_book_qty != nullptr and p_set_top_of_book_premium != nullptr and
                    p_set_top_of_book_last_update_date_time != nullptr);

                    try {

                        std::lock_guard<std::mutex> lock(*lock_mutex);
//                        std::unique_lock<std::mutex> lock(*lock_mutex, std::defer_lock_t{});
//
//                        if (!lock.try_lock())
//                        {return;}

                        p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book.bid_quote().px()));
                        PyObject_CallObject(p_set_top_of_book_price, p_args);

                        p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_of_book.bid_quote().qty()));
                        PyObject_CallObject(p_set_top_of_book_qty, p_args);

                        p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book.bid_quote().premium()));
                        PyObject_CallObject(p_set_top_of_book_premium, p_args);

                        p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(
                                kr_top_of_book.bid_quote().last_update_date_time().c_str(),
                                static_cast<Py_ssize_t>(kr_top_of_book.bid_quote().last_update_date_time().size()),
                                nullptr));
                        PyObject_CallObject(p_set_top_of_book_bid_quote_last_update_date_time, p_args);
                    } catch (std::exception& exception) {
                        std::cerr << "Exception caught: " << exception.what() << std::endl;
                    }

                } else if (kr_side == "ASK") {

                    PyObject* p_set_top_of_book_price = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_ask_quote_px");
                    PyObject* p_set_top_of_book_qty = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_ask_quote_qty");
                    PyObject* p_set_top_of_book_premium = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_ask_quote_premium");
                    PyObject* p_set_top_of_book_ask_quote_last_update_date_time =
                            PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_ask_quote_last_update_date_time");

                    assert(p_set_top_of_book_price != nullptr and
                    p_set_top_of_book_qty != nullptr and p_set_top_of_book_premium != nullptr and
                    p_set_top_of_book_last_update_date_time != nullptr);

                    try {

                        std::lock_guard<std::mutex> lock(*lock_mutex);


                        p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book.ask_quote().px()));
                        PyObject_CallObject(p_set_top_of_book_price, p_args);

                        p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_of_book.ask_quote().qty()));
                        PyObject_CallObject(p_set_top_of_book_qty, p_args);

                        p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book.ask_quote().premium()));
                        PyObject_CallObject(p_set_top_of_book_premium, p_args);

                        p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(
                                kr_top_of_book.ask_quote().last_update_date_time().c_str(),
                                static_cast<Py_ssize_t>(kr_top_of_book.ask_quote().last_update_date_time().size()),
                                nullptr));
                        PyObject_CallObject(p_set_top_of_book_ask_quote_last_update_date_time, p_args);
                    } catch (std::exception& exception) {
                        std::cerr << "Exception caught: " << exception.what() << std::endl;
                    }

                } else {

                    PyObject* p_set_top_of_book_price = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_last_trade_px");
                    PyObject* p_set_top_of_book_qty = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_last_trade_qty");
                    PyObject* p_set_top_of_book_premium = PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_last_trade_premium");
                    PyObject* p_set_top_of_book_last_trade_last_update_date_time =
                            PyObject_GetAttrString(p_mobile_book_container_instance, "set_top_of_book_last_trade_last_update_date_time");

                    assert( p_set_top_of_book_price != nullptr and p_set_top_of_book_qty
                                                                                                           != nullptr and p_set_top_of_book_premium != nullptr and p_set_top_of_book_last_update_date_time != nullptr);

                try {

                    std::lock_guard<std::mutex> lock(*lock_mutex);



                    p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book.last_trade().px()));
                    PyObject_CallObject(p_set_top_of_book_price, p_args);

                    p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_of_book.last_trade().qty()));
                    PyObject_CallObject(p_set_top_of_book_qty, p_args);

                    p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book.last_trade().premium()));
                    PyObject_CallObject(p_set_top_of_book_premium, p_args);

                    p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(
                            kr_top_of_book.last_trade().last_update_date_time().c_str(),
                            static_cast<Py_ssize_t>(kr_top_of_book.last_trade().last_update_date_time().size()),
                            nullptr));
                    PyObject_CallObject(p_set_top_of_book_last_trade_last_update_date_time, p_args);
                } catch (std::exception& exception) {
                    std::cerr << "Exception caught: " << exception.what() << std::endl;
                }

                }

                try {
                    std::lock_guard<std::mutex> lock(*lock_mutex);

                    p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_of_book.total_trading_security_size()));
                    PyObject_CallObject(p_top_of_book_total_trading_security_size, p_args);

                    for (int i = 0; i < kr_top_of_book.market_trade_volume_size(); ++i) {
                        p_result = set_market_trade_volume(p_mobile_book_container_instance,
                                                           kr_top_of_book.market_trade_volume(i));
                        if (!PyObject_IsTrue(p_result)) {

                            p_args = PyTuple_Pack(2,
                                                  PyUnicode_DecodeUTF8(kr_top_of_book.market_trade_volume(i).id().c_str(),
                                                                       static_cast<Py_ssize_t>(kr_top_of_book.market_trade_volume(
                                                                               i).id().size()), nullptr),
                                                  PyLong_FromLong(kr_top_of_book.market_trade_volume(
                                                          i).participation_period_last_trade_qty_sum()));
                            PyObject_CallObject(p_set_top_of_book_mkt_trade_vol_participation_period_last_trade_qty_sum, p_args);

                            p_args = PyTuple_Pack(2,
                                                  PyUnicode_DecodeUTF8(kr_top_of_book.market_trade_volume(i).id().c_str(),
                                                                       static_cast<Py_ssize_t>(kr_top_of_book.market_trade_volume(
                                                                               i).id().size()), nullptr),
                                                  PyLong_FromLong(kr_top_of_book.market_trade_volume(
                                                          i).applicable_period_seconds()));
                            PyObject_CallObject(p_set_top_of_book_mkt_trade_vol_applicable_per_seconds, p_args);
                        }
                    }

                    p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_top_of_book.last_update_date_time().c_str(),
                                                                  static_cast<Py_ssize_t>(kr_top_of_book.last_update_date_time().size()),
                                                                  nullptr));

                    PyObject_CallObject(p_set_top_of_book_last_update_date_time, p_args);
                } catch (std::exception& exception) {
                    std::cerr << "Exception caught: " << exception.what() << std::endl;
                }
            }
        }

        p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "print_tob_obj");
        assert(p_set_func != nullptr);
        PyObject_CallObject(p_set_func, nullptr);


    }

}

extern "C" void create_last_trade_cache(const mobile_book::LastTrade &kr_last_trade_obj, PyObject* p_module,
                                        PyObject* p_mobile_book_container_instance) {

    PyObject* p_set_func = nullptr;
    PyObject* p_market_trade_volume_class = nullptr;
    PyObject* p_market_trade_volume_args = nullptr;
    PyObject* p_market_trade_volume_instance = nullptr;
    PyObject* p_args = nullptr;

    p_market_trade_volume_class = PyObject_GetAttrString(p_module, "MarketTradeVolume");
    p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "set_last_trade");
    p_market_trade_volume_args = PyTuple_Pack(3, PyUnicode_DecodeUTF8(kr_last_trade_obj.market_trade_volume().id().c_str(),
                                                                      static_cast<Py_ssize_t>(kr_last_trade_obj.market_trade_volume().id().size()),
                                                                      nullptr),
                                              PyLong_FromLong(kr_last_trade_obj.market_trade_volume().participation_period_last_trade_qty_sum()),
                                              PyLong_FromLong(kr_last_trade_obj.market_trade_volume().applicable_period_seconds()));
    p_market_trade_volume_instance = PyObject_CallObject(p_market_trade_volume_class, p_market_trade_volume_args);

    p_args = PyTuple_Pack(9, PyLong_FromLong(kr_last_trade_obj.id()),
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
                          p_market_trade_volume_instance);

    PyObject_CallObject(p_set_func, p_args);
}

extern "C" void update_or_create_last_trade(const mobile_book::LastTrade &kr_last_trade_obj) {
    Py_Initialize();

    PyObject* p_mobile_book_container_instance = nullptr;
    PyObject* p_module = nullptr;
    PyObject* p_set_func = nullptr;
    PyObject* p_args = nullptr;
    PyObject* p_result = nullptr;
    PyObject* p_market_trade_volume_class = nullptr;
    PyObject* p_market_trade_volume_instance = nullptr;
    PyObject* p_market_trade_volume_args = nullptr;
    PyObject* p_last_trade_instance = nullptr;
    PyObject* p_mutex = nullptr;

    {
        ::PythonGIL gil;

        p_module = PyImport_ImportModule("mobile_book_cache");
        assert(p_module != nullptr);

        p_mobile_book_container_instance = get_mobile_book_container_instance(kr_last_trade_obj.symbol_n_exch_id().symbol());
        if (!p_mobile_book_container_instance) {
            p_set_func = PyObject_GetAttrString(p_module, "add_container_obj_for_symbol");
            PyObject_CallObject(p_set_func, PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_last_trade_obj.symbol_n_exch_id().symbol().c_str(),
                                                                                 static_cast<Py_ssize_t>(kr_last_trade_obj.symbol_n_exch_id().symbol().size()),
                                                                                 nullptr)));

            p_mobile_book_container_instance = get_mobile_book_container_instance(kr_last_trade_obj.symbol_n_exch_id().symbol());

            create_last_trade_cache(kr_last_trade_obj, p_module, p_mobile_book_container_instance);
        } else {

            p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "get_last_trade");
            p_last_trade_instance = PyObject_CallObject(p_set_func, nullptr);

            if (p_last_trade_instance == Py_None) {
                create_last_trade_cache(kr_last_trade_obj, p_module, p_mobile_book_container_instance);
            } else {
                p_set_func = PyObject_GetAttrString(p_last_trade_instance, "get_mutex");
                if(!p_set_func or PyCallable_Check(p_set_func)) {
                    PyErr_Print();
                }
                p_mutex = PyObject_CallObject(p_set_func, nullptr);
                void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
                std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);

                PyObject* p_set_last_trade_exch_id = PyObject_GetAttrString(p_mobile_book_container_instance, "set_last_trade_exch_id");
                PyObject* p_set_last_trade_exch_time = PyObject_GetAttrString(p_mobile_book_container_instance, "set_last_trade_exch_time");
                PyObject* p_set_last_trade_arrival_time = PyObject_GetAttrString(p_mobile_book_container_instance, "set_last_trade_arrival_time");
                PyObject* p_set_last_trade_px = PyObject_GetAttrString(p_mobile_book_container_instance, "set_last_trade_px");
                PyObject* p_set_last_trade_qty = PyObject_GetAttrString(p_mobile_book_container_instance, "set_last_trade_qty");
                PyObject* p_set_last_trade_premium = PyObject_GetAttrString(p_mobile_book_container_instance, "set_last_trade_premium");
                PyObject* p_set_last_trade_market_trade_volume_participation_period_last_trade_qty_sum =
                        PyObject_GetAttrString(p_mobile_book_container_instance,
                                               "set_last_trade_market_trade_volume_participation_period_last_trade_qty_sum");
                PyObject* p_set_last_trade_market_trade_volume_applicable_period_seconds =
                        PyObject_GetAttrString(p_mobile_book_container_instance,
                                               "set_last_trade_market_trade_volume_applicable_period_seconds");
                assert(p_set_last_trade_exch_id != nullptr && p_set_last_trade_exch_time != nullptr &&
                       p_set_last_trade_arrival_time != nullptr && p_set_last_trade_px != nullptr &&
                       p_set_last_trade_qty != nullptr && p_set_last_trade_premium != nullptr &&
                       p_set_last_trade_market_trade_volume_participation_period_last_trade_qty_sum != nullptr &&
                       p_set_last_trade_market_trade_volume_applicable_period_seconds != nullptr);

                try {
                    std::lock_guard<std::mutex> lock(*lock_mutex);

                    p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_last_trade_obj.symbol_n_exch_id().exch_id().c_str(),
                                                                  static_cast<Py_ssize_t>(kr_last_trade_obj.symbol_n_exch_id().exch_id().size()),
                                                                  nullptr));
                    PyObject_CallObject(p_set_last_trade_exch_id, p_args);

                    p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_last_trade_obj.exch_time().c_str(),
                                                                  static_cast<Py_ssize_t>(kr_last_trade_obj.exch_time().size()),
                                                                  nullptr));
                    PyObject_CallObject(p_set_last_trade_exch_time, p_args);

                    p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_last_trade_obj.arrival_time().c_str(),
                                                                  static_cast<Py_ssize_t>(kr_last_trade_obj.arrival_time().size()),
                                                                  nullptr));
                    PyObject_CallObject(p_set_last_trade_arrival_time, p_args);

                    p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_last_trade_obj.px()));
                    PyObject_CallObject(p_set_last_trade_px, p_args);

                    p_args = PyTuple_Pack(1, PyLong_FromLong(kr_last_trade_obj.qty()));
                    PyObject_CallObject(p_set_last_trade_qty, p_args);

                    p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_last_trade_obj.premium()));
                    PyObject_CallObject(p_set_last_trade_premium, p_args);

                    p_args = PyTuple_Pack(2, PyUnicode_DecodeUTF8(kr_last_trade_obj.market_trade_volume().id().c_str(),
                                                                  static_cast<Py_ssize_t>(kr_last_trade_obj.market_trade_volume().id().size()),
                                                                  nullptr),
                                          PyLong_FromLong(kr_last_trade_obj.market_trade_volume().participation_period_last_trade_qty_sum()));
                    PyObject_CallObject(p_set_last_trade_market_trade_volume_participation_period_last_trade_qty_sum, p_args);

                    p_args = PyTuple_Pack(2, PyUnicode_DecodeUTF8(kr_last_trade_obj.market_trade_volume().id().c_str(),
                                                                  static_cast<Py_ssize_t>(kr_last_trade_obj.market_trade_volume().id().size()),
                                                                  nullptr));
                    PyObject_CallObject(p_set_last_trade_market_trade_volume_applicable_period_seconds, p_args);

                } catch (std::exception& exception) {
                    std::cerr << "Exception caught: " << exception.what() << std::endl;
                }
            }
        }

        p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "print_last_trade_obj");
        assert(p_set_func != nullptr);
        PyObject_CallObject(p_set_func, nullptr);

    }
}

extern "C" void create_market_depth_cache(const mobile_book::MarketDepth &kr_market_depth_obj, PyObject* p_mobile_book_container_instance) {
    PyObject *p_set_func = nullptr;
    PyObject *p_args = nullptr;

    if (kr_market_depth_obj.side() == mobile_book::BID) {
        p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth");
        p_args = PyTuple_Pack(14, PyLong_FromLong(kr_market_depth_obj.id()),
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
                              PyFloat_FromDouble(kr_market_depth_obj.premium()),
                              PyUnicode_DecodeUTF8(kr_market_depth_obj.market_maker().c_str(),
                                                   static_cast<Py_ssize_t>(kr_market_depth_obj.market_maker().size()),
                                                   nullptr),
                              PyBool_FromLong(kr_market_depth_obj.is_smart_depth()),
                              PyFloat_FromDouble(kr_market_depth_obj.cumulative_notional()),
                              PyLong_FromLong(kr_market_depth_obj.cumulative_qty()),
                              PyFloat_FromDouble(kr_market_depth_obj.cumulative_avg_px()));

        PyObject_CallObject(p_set_func, p_args);
    } else {

        p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth");
        p_args = PyTuple_Pack(14, PyLong_FromLong(kr_market_depth_obj.id()),
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
                              PyFloat_FromDouble(kr_market_depth_obj.premium()),
                              PyUnicode_DecodeUTF8(kr_market_depth_obj.market_maker().c_str(),
                                                   static_cast<Py_ssize_t>(kr_market_depth_obj.market_maker().size()),
                                                   nullptr),
                              PyBool_FromLong(kr_market_depth_obj.is_smart_depth()),
                              PyFloat_FromDouble(kr_market_depth_obj.cumulative_notional()),
                              PyLong_FromLong(kr_market_depth_obj.cumulative_qty()),
                              PyFloat_FromDouble(kr_market_depth_obj.cumulative_avg_px()));

        PyObject_CallObject(p_set_func, p_args);
    }

}


extern "C" void update_or_create_market_depth_cache(const mobile_book::MarketDepth &kr_market_depth_obj) {

    Py_Initialize();

    PyObject* p_mobile_book_container_instance = nullptr;
    PyObject* p_market_depth_instance = nullptr;
    PyObject* p_module = nullptr;
    PyObject* p_set_func = nullptr;
    PyObject* p_args = nullptr;
    PyObject* p_mutex = nullptr;

    {
        ::PythonGIL gil;
        p_module = PyImport_ImportModule("mobile_book_cache");
        assert(p_module != nullptr);

        p_mobile_book_container_instance = get_mobile_book_container_instance(kr_market_depth_obj.symbol());
        if (!p_mobile_book_container_instance) {

            PyObject *p_add_container_obj_for_symbol = PyObject_GetAttrString(p_module, "add_container_obj_for_symbol");
            p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_market_depth_obj.symbol().c_str(),
                                                          static_cast<Py_ssize_t>(kr_market_depth_obj.symbol().size()),
                                                          nullptr));
            PyObject_CallObject(p_add_container_obj_for_symbol, p_args);

            p_mobile_book_container_instance = get_mobile_book_container_instance(kr_market_depth_obj.symbol());

            create_market_depth_cache(kr_market_depth_obj, p_mobile_book_container_instance);

        } else {

            if (kr_market_depth_obj.side() == mobile_book::TickType::BID) {
                PyObject* p_get_bid_market_depth_from_depth = PyObject_GetAttrString(p_mobile_book_container_instance, "get_bid_market_depth_from_depth");
                PyObject* p_set_bid_market_depth_symbol = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_symbol");
                PyObject* p_set_bid_market_depth_exch_time = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_exch_time");
                PyObject* p_set_bid_market_depth_arrival_time = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_arrival_time");
                PyObject* p_set_bid_market_depth_side = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_side");
                PyObject* p_set_bid_market_depth_px = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_px");
                PyObject* p_set_bid_market_depth_qty = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_qty");
                PyObject* p_set_bid_market_depth_market_maker = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_market_maker");
                PyObject* p_set_bid_market_depth_is_smart_depth = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_is_smart_depth");
                PyObject* p_set_bid_market_depth_cumulative_notional = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_cumulative_notional");
                PyObject* p_set_bid_market_depth_cumulative_qty = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_cumulative_qty");
                PyObject* p_set_bid_market_depth_cumulative_avg_px = PyObject_GetAttrString(p_mobile_book_container_instance, "set_bid_market_depth_cumulative_avg_px");
                assert(p_get_bid_market_depth_from_depth != nullptr && p_set_bid_market_depth_symbol != nullptr &&
                p_set_bid_market_depth_exch_time != nullptr &&
                p_set_bid_market_depth_arrival_time != nullptr && p_set_bid_market_depth_side != nullptr &&
                p_set_bid_market_depth_px != nullptr && p_set_bid_market_depth_qty != nullptr &&
                p_set_bid_market_depth_market_maker != nullptr && p_set_bid_market_depth_is_smart_depth != nullptr &&
                p_set_bid_market_depth_cumulative_notional != nullptr && p_set_bid_market_depth_cumulative_qty &&
                p_set_bid_market_depth_cumulative_avg_px != nullptr);

                p_args = PyTuple_Pack(1, PyLong_FromLong(kr_market_depth_obj.position()));
                p_market_depth_instance = PyObject_CallObject(p_get_bid_market_depth_from_depth, p_args);
                if (p_market_depth_instance == Py_None) {
                    create_market_depth_cache(kr_market_depth_obj, p_mobile_book_container_instance);
                } else {
                    p_set_func = PyObject_GetAttrString(p_market_depth_instance, "get_mutex");
                    p_mutex = PyObject_CallObject(p_set_func, nullptr);
                    void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
                    std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);

                    {
                        std::lock_guard<std::mutex> lock(*lock_mutex);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyUnicode_DecodeUTF8(kr_market_depth_obj.symbol().c_str(),
                                                                   static_cast<Py_ssize_t>(kr_market_depth_obj.symbol().size()),
                                                                   nullptr));
                        PyObject_CallObject(p_set_bid_market_depth_symbol, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyUnicode_DecodeUTF8(kr_market_depth_obj.exch_time().c_str(),
                                                                   static_cast<Py_ssize_t>(kr_market_depth_obj.exch_time().size()),
                                                                   nullptr));
                        PyObject_CallObject(p_set_bid_market_depth_exch_time, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyUnicode_DecodeUTF8(kr_market_depth_obj.arrival_time().c_str(),
                                                                   static_cast<Py_ssize_t>(kr_market_depth_obj.arrival_time().size()),
                                                                   nullptr));
                        PyObject_CallObject(p_set_bid_market_depth_arrival_time, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyLong_FromLong(kr_market_depth_obj.side()));
                        PyObject_CallObject(p_set_bid_market_depth_side, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyFloat_FromDouble(kr_market_depth_obj.px()));
                        PyObject_CallObject(p_set_bid_market_depth_px, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyLong_FromLong(kr_market_depth_obj.qty()));
                        PyObject_CallObject(p_set_bid_market_depth_qty, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyUnicode_DecodeUTF8(kr_market_depth_obj.market_maker().c_str(),
                                                                   static_cast<Py_ssize_t>(kr_market_depth_obj.market_maker().size()),
                                                                   nullptr));
                        PyObject_CallObject(p_set_bid_market_depth_market_maker, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyLong_FromLong(kr_market_depth_obj.is_smart_depth()));
                        PyObject_CallObject(p_set_bid_market_depth_is_smart_depth, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyFloat_FromDouble(kr_market_depth_obj.cumulative_notional()));
                        PyObject_CallObject(p_set_bid_market_depth_cumulative_notional, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyLong_FromLong(kr_market_depth_obj.cumulative_qty()));
                        PyObject_CallObject(p_set_bid_market_depth_cumulative_qty, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyFloat_FromDouble(kr_market_depth_obj.cumulative_avg_px()));
                        PyObject_CallObject(p_set_bid_market_depth_cumulative_avg_px, p_args);
                    }
                }


            } else {
                PyObject* p_get_ask_market_depth_from_depth = PyObject_GetAttrString(p_mobile_book_container_instance, "get_ask_market_depth_from_depth");
                PyObject* p_set_ask_market_depth_symbol = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_symbol");
                PyObject* p_set_ask_market_depth_exch_time = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_exch_time");
                PyObject* p_set_ask_market_depth_arrival_time = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_arrival_time");
                PyObject* p_set_ask_market_depth_side = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_side");
                PyObject* p_set_ask_market_depth_px = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_px");
                PyObject* p_set_ask_market_depth_qty = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_qty");
                PyObject* p_set_ask_market_depth_market_maker = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_market_maker");
                PyObject* p_set_ask_market_depth_is_smart_depth = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_is_smart_depth");
                PyObject* p_set_ask_market_depth_cumulative_notional = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_cumulative_notional");
                PyObject* p_set_ask_market_depth_cumulative_qty = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_cumulative_qty");
                PyObject* p_set_ask_market_depth_cumulative_avg_px = PyObject_GetAttrString(p_mobile_book_container_instance, "set_ask_market_depth_cumulative_avg_px");
                assert(p_get_ask_market_depth_from_depth != nullptr && p_set_ask_market_depth_symbol != nullptr &&
                       p_set_ask_market_depth_exch_time != nullptr &&
                       p_set_ask_market_depth_arrival_time != nullptr && p_set_ask_market_depth_side != nullptr &&
                       p_set_ask_market_depth_px != nullptr && p_set_ask_market_depth_qty != nullptr &&
                       p_set_ask_market_depth_market_maker != nullptr && p_set_ask_market_depth_is_smart_depth != nullptr &&
                       p_set_ask_market_depth_cumulative_notional != nullptr && p_set_ask_market_depth_cumulative_qty &&
                       p_set_ask_market_depth_cumulative_avg_px != nullptr);

                p_args = PyTuple_Pack(1, PyLong_FromLong(kr_market_depth_obj.position()));
                p_market_depth_instance = PyObject_CallObject(p_get_ask_market_depth_from_depth, p_args);
                if (p_market_depth_instance == Py_None) {
                    create_market_depth_cache(kr_market_depth_obj, p_mobile_book_container_instance);
                } else {
                    p_set_func = PyObject_GetAttrString(p_market_depth_instance, "get_mutex");
                    p_mutex = PyObject_CallObject(p_set_func, nullptr);
                    void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
                    std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);

                    {
                        std::lock_guard<std::mutex> lock(*lock_mutex);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyUnicode_DecodeUTF8(kr_market_depth_obj.symbol().c_str(),
                                                                   static_cast<Py_ssize_t>(kr_market_depth_obj.symbol().size()),
                                                                   nullptr));
                        PyObject_CallObject(p_set_ask_market_depth_symbol, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyUnicode_DecodeUTF8(kr_market_depth_obj.exch_time().c_str(),
                                                                   static_cast<Py_ssize_t>(kr_market_depth_obj.exch_time().size()),
                                                                   nullptr));
                        PyObject_CallObject(p_set_ask_market_depth_exch_time, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyUnicode_DecodeUTF8(kr_market_depth_obj.arrival_time().c_str(),
                                                                   static_cast<Py_ssize_t>(kr_market_depth_obj.arrival_time().size()),
                                                                   nullptr));
                        PyObject_CallObject(p_set_ask_market_depth_arrival_time, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyLong_FromLong(kr_market_depth_obj.side()));
                        PyObject_CallObject(p_set_ask_market_depth_side, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyFloat_FromDouble(kr_market_depth_obj.px()));
                        PyObject_CallObject(p_set_ask_market_depth_px, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyLong_FromLong(kr_market_depth_obj.qty()));
                        PyObject_CallObject(p_set_ask_market_depth_qty, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyUnicode_DecodeUTF8(kr_market_depth_obj.market_maker().c_str(),
                                                                   static_cast<Py_ssize_t>(kr_market_depth_obj.market_maker().size()),
                                                                   nullptr));
                        PyObject_CallObject(p_set_ask_market_depth_market_maker, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyLong_FromLong(kr_market_depth_obj.is_smart_depth()));
                        PyObject_CallObject(p_set_ask_market_depth_is_smart_depth, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyFloat_FromDouble(kr_market_depth_obj.cumulative_notional()));
                        PyObject_CallObject(p_set_ask_market_depth_cumulative_notional, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyLong_FromLong(kr_market_depth_obj.cumulative_qty()));
                        PyObject_CallObject(p_set_ask_market_depth_cumulative_qty, p_args);

                        p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                                              PyFloat_FromDouble(kr_market_depth_obj.cumulative_avg_px()));
                        PyObject_CallObject(p_set_ask_market_depth_cumulative_avg_px, p_args);
                    }
                }



            }

        }


        if (kr_market_depth_obj.side() == mobile_book::TickType::BID) {
            p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "print_bid_market_depth_obj");
        } else {
            p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, "print_ask_market_depth_obj");
        }
        if (!p_set_func or !PyCallable_Check(p_set_func)) {
            PyErr_Print();
            return;
        }

        PyObject_CallObject(p_set_func, nullptr);
    }
}