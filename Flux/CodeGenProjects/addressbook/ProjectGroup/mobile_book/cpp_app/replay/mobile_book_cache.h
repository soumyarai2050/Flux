#pragma once

#include <iostream>
#include <Python.h>

#include "mobile_book_service.pb.h"
#include "utility_functions.h"
#include "string_util.h"
#include "add_or_get_container_from_py_cache.h"
#include "logger.h"


namespace mobile_book_handler {
    namespace market_cache {

        class LastBarterCache {
        public:
            static void create_last_barter_cache(const std::string &kr_symbol) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;

                    PyObject* p_get_mobile_book_container_object =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_symbol);

                    if (p_get_mobile_book_container_object == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_symbol);
                        return;
                    }
                    PyObject* p_set_last_barter_last_barter_function =
                        PyObject_GetAttrString(
                            p_get_mobile_book_container_object, mobile_book_handler::set_last_barter_key.c_str());

                    PyObject* p_args = PyTuple_Pack(9, PyLong_FromLong(1),
                        PyUnicode_DecodeUTF8(kr_symbol.c_str(), static_cast<Py_ssize_t>(kr_symbol.size()), nullptr),
                        Py_None, Py_None, Py_None, Py_None, Py_None, Py_None, Py_None);
                    PyObject_CallObject(p_set_last_barter_last_barter_function, p_args);
                    auto get_last_barter = PyObject_GetAttrString(p_get_mobile_book_container_object,
                        mobile_book_handler::get_last_barter_key.c_str());
                    auto last_barter_obj = PyObject_CallObject(get_last_barter, nullptr);
                    if (last_barter_obj == Py_None) {
                        std::cout << "Last Barter Cache is none for symbol: " << kr_symbol << "\n";
                    } else {
                        std::cout << "Last Barter Cache created for symbol: " << kr_symbol << "\n";
                    }
                }
            }

            static void* get_last_barter_mutex(const std::string &kr_symbol) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;

                    PyObject* p_get_mobile_book_container_object =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_symbol);

                    if (p_get_mobile_book_container_object == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_symbol);
                        return nullptr;
                    }

                    PyObject* p_get_last_barter_function =
                        PyObject_GetAttrString(
                            p_get_mobile_book_container_object, mobile_book_handler::get_last_barter_key.c_str());
                    PyObject* p_last_trde_object = PyObject_CallObject(p_get_last_barter_function, nullptr);

                    if (p_last_trde_object == Py_None) {
                        auto err = std::format("Failed to reterive last_barter obj from container for symbol: {}", kr_symbol);
                        LOG_ERROR_IMPL(GetLogger(), "{}", err);
                        return nullptr;
                    }

                    PyObject* p_last_barter_mutex_func = PyObject_GetAttrString(
                        p_last_trde_object, mobile_book_handler::get_mutex_key.c_str());
                    PyObject* p_last_barter_mutex;
                    try {
                        p_last_barter_mutex = PyObject_CallObject(p_last_barter_mutex_func, nullptr);
                    } catch (std::exception& ex) {
                        LOG_ERROR_IMPL(GetLogger(), "Filed to reterive mutex obj from container for symbol: {}, "
                                                    "exception: {}", kr_symbol, ex.what());
                        return nullptr;
                    }
                    return PyLong_AsVoidPtr(p_last_barter_mutex);
                }
            }

            static bool update_last_barter_cache(const mobile_book::LastBarter &kr_last_barter_obj) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;

                    PyObject* p_args;
                    PyObject* p_mobile_book_container_instance =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_last_barter_obj.symbol_n_exch_id().symbol());

                    if (p_mobile_book_container_instance == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_last_barter_obj.symbol_n_exch_id().symbol());
                        return false;
                    }

                    PyObject* p_set_last_barter_exch_id = PyObject_GetAttrString(p_mobile_book_container_instance,
                        set_last_barter_exch_id_key.c_str());
                    PyObject* p_set_last_barter_exch_time = PyObject_GetAttrString(p_mobile_book_container_instance,
                        set_last_barter_exch_time_key.c_str());
                    PyObject* p_set_last_barter_arrival_time = PyObject_GetAttrString(p_mobile_book_container_instance,
                        set_last_barter_arrival_time_key.c_str());
                    PyObject* p_set_last_barter_px = PyObject_GetAttrString(p_mobile_book_container_instance,
                        set_last_barter_px_key.c_str());
                    PyObject* p_set_last_barter_qty = PyObject_GetAttrString(p_mobile_book_container_instance,
                        set_last_barter_qty_key.c_str());
                    PyObject* p_set_last_barter_premium = PyObject_GetAttrString(p_mobile_book_container_instance,
                        set_last_barter_premium_key.c_str());
                    PyObject* p_set_last_barter_market_barter_volume_participation_period_last_barter_qty_sum =
                        PyObject_GetAttrString(
                            p_mobile_book_container_instance,
                            set_last_barter_market_barter_volume_participation_period_last_barter_qty_sum_key.c_str());
                    PyObject* p_set_last_barter_market_barter_volume_applicable_period_seconds =
                        PyObject_GetAttrString(p_mobile_book_container_instance,
                            set_last_barter_market_barter_volume_applicable_period_seconds_key.c_str());

                    try {

                        p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_last_barter_obj.symbol_n_exch_id().exch_id().c_str(),
                                                                      static_cast<Py_ssize_t>(
                                                                          kr_last_barter_obj.symbol_n_exch_id().exch_id().size()),
                                                                      nullptr));
                        PyObject_CallObject(p_set_last_barter_exch_id, p_args);


                        std::string exch_time;
                        FluxCppCore::format_time(kr_last_barter_obj.exch_time(), exch_time);
                        p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(exch_time.c_str(),
                                                                      static_cast<Py_ssize_t>(
                                                                          exch_time.size()),
                                                                      nullptr));
                        PyObject_CallObject(p_set_last_barter_exch_time, p_args);

                        std::string arrival_time;
                        FluxCppCore::format_time(kr_last_barter_obj.arrival_time(), arrival_time);
                        p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(arrival_time.c_str(),
                                                                      static_cast<Py_ssize_t>(
                                                                          arrival_time.size()),
                                                                      nullptr));
                        PyObject_CallObject(p_set_last_barter_arrival_time, p_args);

                        p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_last_barter_obj.px()));
                        PyObject_CallObject(p_set_last_barter_px, p_args);

                        p_args = PyTuple_Pack(1, PyLong_FromLong(kr_last_barter_obj.qty()));
                        PyObject_CallObject(p_set_last_barter_qty, p_args);

                        p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_last_barter_obj.premium()));
                        PyObject_CallObject(p_set_last_barter_premium, p_args);

                        p_args = PyTuple_Pack(1, PyLong_FromLong(
                            kr_last_barter_obj.market_barter_volume().participation_period_last_barter_qty_sum()));
                        PyObject_CallObject(
                            p_set_last_barter_market_barter_volume_participation_period_last_barter_qty_sum, p_args);

                        p_args = PyTuple_Pack(1, PyLong_FromLong(
                            kr_last_barter_obj.market_barter_volume().applicable_period_seconds()));
                        PyObject_CallObject(
                            p_set_last_barter_market_barter_volume_applicable_period_seconds, p_args);

                    } catch (std::exception& exception) {
                        LOG_ERROR_IMPL(GetLogger(), "Exception caught while updating last_barter cache: "
                                                    "last_barter obj: {};;; exception: {}",
                                                    kr_last_barter_obj.DebugString(), exception.what());
                        return false;
                    }
                }
                return true;
            }
        };

        class TopOfBookCache {
        public:
            static void create_top_of_book_cache(const std::string& kr_symbol) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;

                    PyObject* p_get_mobile_book_container_object =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_symbol);

                    if (p_get_mobile_book_container_object == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_symbol);
                        return;
                    }

                    PyObject* p_set_top_of_book_function =
                        PyObject_GetAttrString(
                            p_get_mobile_book_container_object, mobile_book_handler::set_top_of_book_key.c_str());
                    PyObject* p_args = PyTuple_Pack(17, PyLong_FromLong(1),
                        PyUnicode_DecodeUTF8(kr_symbol.c_str(), static_cast<Py_ssize_t>(kr_symbol.size()),
                            nullptr),
                            Py_None, Py_None, Py_None,Py_None, Py_None, Py_None, Py_None, Py_None, Py_None, Py_None,
                            Py_None,Py_None, Py_None, Py_None, Py_None);
                    PyObject_CallObject(p_set_top_of_book_function, p_args);

                }
            }

            static void* get_top_of_book_mutex(const std::string &kr_symbol) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;

                    PyObject* p_get_mobile_book_container_object =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_symbol);

                    if (p_get_mobile_book_container_object == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_symbol);
                        return nullptr;
                    }

                    PyObject* p_get_top_of_book_function =
                        PyObject_GetAttrString(
                            p_get_mobile_book_container_object, mobile_book_handler::get_top_of_book_key.c_str());
                    PyObject* p_top_of_book_object = PyObject_CallObject(p_get_top_of_book_function, nullptr);

                    if (p_top_of_book_object == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "failed to reterive top_of_book obj for symbol: {}", kr_symbol);
                        return nullptr;
                    }

                    PyObject* p_last_barter_mutex_func = PyObject_GetAttrString(
                        p_top_of_book_object, mobile_book_handler::get_mutex_key.c_str());
                    PyObject* p_top_of_book_mutex;
                    try {
                        p_top_of_book_mutex = PyObject_CallObject(p_last_barter_mutex_func, nullptr);
                    } catch (std::exception& ex) {
                        LOG_ERROR_IMPL(GetLogger(), "failed to reterive mutex from top_of_book obj for "
                                                    "symbol: {}, exception: {}", kr_symbol, ex.what());
                        return nullptr;
                    }
                    return PyLong_AsVoidPtr(p_top_of_book_mutex);
                }
            }

            static bool update_top_of_book_cache(const mobile_book::TopOfBook &kr_top_of_book_obj) {
                Py_Initialize();
                bool status{false};
                {
                    FluxCppCore::PythonGIL gil;
                    PyObject* p_get_mobile_book_container_object =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_top_of_book_obj.symbol());

                    if (p_get_mobile_book_container_object == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_top_of_book_obj.symbol());
                        return false;
                    }

                    if (kr_top_of_book_obj.has_bid_quote()) {
                        PyObject* p_get_bid_quote_function = PyObject_GetAttrString(
                            p_get_mobile_book_container_object, get_top_of_book_bid_quote_key.c_str());
                        PyObject* p_get_bid_quote_obj = PyObject_CallObject(p_get_bid_quote_function, nullptr);
                        if (p_get_bid_quote_obj != Py_None) {
                            status = update_top_of_book_bid_quote(kr_top_of_book_obj, p_get_mobile_book_container_object);
                        } else {
                            status = create_top_of_bid_quote_cache(kr_top_of_book_obj, p_get_mobile_book_container_object);
                        }
                    }

                    if (kr_top_of_book_obj.has_ask_quote()) {
                        PyObject* p_get_ask_quote_function = PyObject_GetAttrString(
                            p_get_mobile_book_container_object, get_top_of_book_ask_quote_key.c_str());
                        PyObject* p_get_ask_quote_obj = PyObject_CallObject(p_get_ask_quote_function, nullptr);
                        if (p_get_ask_quote_obj != Py_None) {
                            status = update_top_of_book_ask_quote(kr_top_of_book_obj, p_get_mobile_book_container_object);
                        } else {
                            status = create_top_of_ask_quote_cache(kr_top_of_book_obj, p_get_mobile_book_container_object);
                        }
                    }

                    if (kr_top_of_book_obj.has_last_barter()) {
                        PyObject* p_get_last_barter_function = PyObject_GetAttrString(
                            p_get_mobile_book_container_object, get_top_of_book_last_barter_key.c_str());
                        PyObject* p_get_last_barter_obj = PyObject_CallObject(p_get_last_barter_function, nullptr);
                        if (p_get_last_barter_obj != Py_None) {
                            status = update_top_of_book_last_barter(kr_top_of_book_obj, p_get_mobile_book_container_object);
                        } else {
                            status = create_top_of_last_barter_cache(kr_top_of_book_obj, p_get_mobile_book_container_object);
                        }
                    }
                }
                return status;
            }

            [[nodiscard]] static bool create_top_of_bid_quote_cache(const mobile_book::TopOfBook &kr_top_of_book_obj,
                PyObject* p_mobile_book_container_instance) {

                PyObject* set_top_of_book_bid_quote_func = PyObject_GetAttrString(
                    p_mobile_book_container_instance, set_top_of_book_bid_quote_key.c_str());
                PyObject* p_args = FluxCppCore::MessageTypeToPythonArgs::message_type_to_python_args(
                    kr_top_of_book_obj.bid_quote());
                auto top_of_book_update_status = PyObject_CallObject(set_top_of_book_bid_quote_func, p_args);
                return PyObject_IsTrue(top_of_book_update_status) ? true : false;
            }

            [[nodiscard]] static bool create_top_of_ask_quote_cache(const mobile_book::TopOfBook &kr_top_of_book_obj,
                PyObject* p_mobile_book_container_instance) {

                PyObject* set_top_of_book_ask_quote_func = PyObject_GetAttrString(
                    p_mobile_book_container_instance, set_top_of_book_ask_quote_key.c_str());
                PyObject* p_args = FluxCppCore::MessageTypeToPythonArgs::message_type_to_python_args(
                    kr_top_of_book_obj.ask_quote());
                auto top_of_book_update_status = PyObject_CallObject(set_top_of_book_ask_quote_func, p_args);
                return PyObject_IsTrue(top_of_book_update_status) ? true : false;
            }

            [[nodiscard]] static bool create_top_of_last_barter_cache(const mobile_book::TopOfBook &kr_top_of_book_obj,
                PyObject* p_mobile_book_container_instance) {

                PyObject* set_top_of_book_last_barter_func = PyObject_GetAttrString(
                    p_mobile_book_container_instance, set_top_of_book_last_barter_key.c_str());
                PyObject* p_args = FluxCppCore::MessageTypeToPythonArgs::message_type_to_python_args(
                    kr_top_of_book_obj.last_barter());
                auto top_of_book_update_status = PyObject_CallObject(set_top_of_book_last_barter_func, p_args);
                return PyObject_IsTrue(top_of_book_update_status) ? true : false;
            }

            [[nodiscard]] static bool update_top_of_book_bid_quote(const mobile_book::TopOfBook &kr_top_book_obj,
                PyObject* p_mobile_book_container_instance) {

                PyObject* p_args;

                PyObject* p_set_top_of_book_price = PyObject_GetAttrString(p_mobile_book_container_instance,
                    set_top_of_book_bid_quote_px_key.c_str());
                PyObject* p_set_top_of_book_qty = PyObject_GetAttrString(p_mobile_book_container_instance,
                    set_top_of_book_bid_quote_qty_key.c_str());
                PyObject* p_set_top_of_book_premium = PyObject_GetAttrString(p_mobile_book_container_instance,
                    set_top_of_book_bid_quote_premium_key.c_str());
                PyObject* p_set_top_of_book_bid_quote_last_update_date_time  =
                        PyObject_GetAttrString(p_mobile_book_container_instance,
                            set_top_of_book_bid_quote_last_update_date_time_key.c_str());

                try {

                    p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_book_obj.bid_quote().px()));
                    PyObject_CallObject(p_set_top_of_book_price, p_args);

                    p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_book_obj.bid_quote().qty()));
                    PyObject_CallObject(p_set_top_of_book_qty, p_args);

                    p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_book_obj.bid_quote().premium()));
                    PyObject_CallObject(p_set_top_of_book_premium, p_args);

                    std::string bid_quote_last_update_date_time;
                    FluxCppCore::format_time(kr_top_book_obj.bid_quote().last_update_date_time(), bid_quote_last_update_date_time);
                    p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(
                            bid_quote_last_update_date_time.c_str(),
                            static_cast<Py_ssize_t>(bid_quote_last_update_date_time.size()),
                            nullptr));
                    PyObject_CallObject(
                        p_set_top_of_book_bid_quote_last_update_date_time, p_args);
                    update_top_of_book_top_lev_fld(kr_top_book_obj, p_mobile_book_container_instance);
                } catch (std::exception& exception) {
                    LOG_ERROR_IMPL(GetLogger(), "Failed to update top_of_book, reason: {}", exception.what());
                    return false;
                }
                return true;
            }

            [[nodiscard]] static bool update_top_of_book_ask_quote(const mobile_book::TopOfBook &kr_top_of_book_obj,
                 PyObject* p_mobile_book_container_instance) {

                PyObject* p_set_top_of_book_price = PyObject_GetAttrString(p_mobile_book_container_instance,
                    set_top_of_book_ask_quote_px_key.c_str());
                PyObject* p_set_top_of_book_qty = PyObject_GetAttrString(p_mobile_book_container_instance,
                    set_top_of_book_ask_quote_qty_key.c_str());
                PyObject* p_set_top_of_book_premium = PyObject_GetAttrString(p_mobile_book_container_instance,
                    set_top_of_book_ask_quote_premium_key.c_str());
                PyObject* p_set_top_of_book_ask_quote_last_update_date_time =
                        PyObject_GetAttrString(p_mobile_book_container_instance,
                            set_top_of_book_ask_quote_last_update_date_time_key.c_str());;

                PyObject* p_args;

                try {

                    p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book_obj.ask_quote().px()));
                    PyObject_CallObject(p_set_top_of_book_price, p_args);

                    p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_of_book_obj.ask_quote().qty()));
                    PyObject_CallObject(p_set_top_of_book_qty, p_args);

                    p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book_obj.ask_quote().premium()));
                    PyObject_CallObject(p_set_top_of_book_premium, p_args);

                    std::string ask_quote_last_update_date_time;
                    FluxCppCore::format_time(kr_top_of_book_obj.ask_quote().last_update_date_time(), ask_quote_last_update_date_time);
                    p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(
                            ask_quote_last_update_date_time.c_str(),
                            static_cast<Py_ssize_t>(ask_quote_last_update_date_time.size()),
                            nullptr));

                    PyObject_CallObject(p_set_top_of_book_ask_quote_last_update_date_time, p_args);
                    update_top_of_book_top_lev_fld(kr_top_of_book_obj, p_mobile_book_container_instance);
                } catch (std::exception &exception) {
                    LOG_ERROR_IMPL(GetLogger(), "Failed to update top_of_book, reason: {}", exception.what());
                    return false;
                }
                return true;
            }

            [[nodiscard]] static bool update_top_of_book_last_barter(const mobile_book::TopOfBook &kr_top_of_book_obj,
                 PyObject* p_mobile_book_container_instance) {

                PyObject* p_set_top_of_book_price = PyObject_GetAttrString(p_mobile_book_container_instance,
                    set_top_of_book_last_barter_px_key.c_str());
                PyObject* p_set_top_of_book_qty = PyObject_GetAttrString(p_mobile_book_container_instance,
                    set_top_of_book_last_barter_qty_key.c_str());
                PyObject* p_set_top_of_book_premium = PyObject_GetAttrString(p_mobile_book_container_instance,
                    set_top_of_book_last_barter_premium_key.c_str());
                PyObject* p_set_top_of_book_last_barter_last_update_date_time =
                        PyObject_GetAttrString(p_mobile_book_container_instance,
                            set_top_of_book_last_barter_last_update_date_time_key.c_str());

                PyObject* p_args;
                try {

                    p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book_obj.last_barter().px()));
                    PyObject_CallObject(p_set_top_of_book_price, p_args);

                    p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_of_book_obj.last_barter().qty()));
                    PyObject_CallObject(p_set_top_of_book_qty, p_args);

                    p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book_obj.last_barter().premium()));
                    PyObject_CallObject(p_set_top_of_book_premium, p_args);

                    std::string last_barter_last_update_date_time;
                    FluxCppCore::format_time(kr_top_of_book_obj.last_barter().last_update_date_time(), last_barter_last_update_date_time);
                    p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(
                            last_barter_last_update_date_time.c_str(),
                            static_cast<Py_ssize_t>(last_barter_last_update_date_time.size()),
                            nullptr));
                    PyObject_CallObject(p_set_top_of_book_last_barter_last_update_date_time, p_args);
                    update_top_of_book_top_lev_fld(kr_top_of_book_obj, p_mobile_book_container_instance);
                } catch (std::exception& exception) {
                    LOG_ERROR_IMPL(GetLogger(), "Failed to update top_of_book, reason: {}", exception.what());
                    return false;
                }
                return true;
            }

            static void update_top_of_book_top_lev_fld(const mobile_book::TopOfBook &kr_top_of_book_obj,
                 PyObject* p_mobile_book_container_instance) {

                PyObject* p_top_of_book_total_bartering_security_size = PyObject_GetAttrString(
                    p_mobile_book_container_instance, set_top_of_book_total_bartering_security_size_key.c_str());
                PyObject* p_set_top_of_book_mkt_barter_vol_participation_period_last_barter_qty_sum =
                        PyObject_GetAttrString(
                            p_mobile_book_container_instance,
                            set_top_of_book_market_barter_volume_participation_period_last_barter_qty_sum_key.c_str());
                PyObject* p_set_top_of_book_mkt_barter_vol_applicable_per_seconds =
                        PyObject_GetAttrString(p_mobile_book_container_instance,
                                               set_top_of_book_market_barter_volume_applicable_period_seconds_key.c_str());
                PyObject* p_set_top_of_book_last_update_date_time = PyObject_GetAttrString(
                    p_mobile_book_container_instance, set_top_of_book_last_update_date_time_key.c_str());

                PyObject* p_args = nullptr;
                PyObject* p_result = nullptr;

                try {
                    p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_of_book_obj.total_bartering_security_size()));
                    PyObject_CallObject(p_top_of_book_total_bartering_security_size, p_args);

                    for (int i = 0; i < kr_top_of_book_obj.market_barter_volume_size(); ++i) {
                        p_result = set_market_barter_volume(p_mobile_book_container_instance,
                                                           kr_top_of_book_obj.market_barter_volume(i));
                        if (!PyObject_IsTrue(p_result)) {

                            p_args = PyTuple_Pack(2,
                                                  PyUnicode_DecodeUTF8(kr_top_of_book_obj.market_barter_volume(i).id().c_str(),
                                                                       static_cast<Py_ssize_t>(
                                                                           kr_top_of_book_obj.market_barter_volume(
                                                                               i).id().size()), nullptr),
                                                  PyLong_FromLong(kr_top_of_book_obj.market_barter_volume(
                                                          i).participation_period_last_barter_qty_sum()));
                            PyObject_CallObject(
                                p_set_top_of_book_mkt_barter_vol_participation_period_last_barter_qty_sum, p_args);

                            p_args = PyTuple_Pack(2,
                                                  PyUnicode_DecodeUTF8(kr_top_of_book_obj.market_barter_volume(i).id().c_str(),
                                                                       static_cast<Py_ssize_t>(
                                                                           kr_top_of_book_obj.market_barter_volume(
                                                                               i).id().size()), nullptr),
                                                  PyLong_FromLong(kr_top_of_book_obj.market_barter_volume(
                                                          i).applicable_period_seconds()));
                            PyObject_CallObject(p_set_top_of_book_mkt_barter_vol_applicable_per_seconds, p_args);
                        }
                    }

                    std::string last_update_date_time;
                    FluxCppCore::format_time(kr_top_of_book_obj.last_update_date_time(), last_update_date_time);
                    p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(last_update_date_time.c_str(),
                                                                  static_cast<Py_ssize_t>(
                                                                      last_update_date_time.size()),
                                                                  nullptr));

                    PyObject_CallObject(p_set_top_of_book_last_update_date_time, p_args);
                } catch (std::exception& exception) {
                    auto err = std::format("Failed: top_of_book cache update, reason: {}, top_ob_book obj: {}", exception.what(), kr_top_of_book_obj.DebugString());
                    LOG_ERROR_IMPL(GetLogger(), "{}", err);
                }
            }

            static PyObject* set_market_barter_volume(PyObject* p_mobile_book_container_instance,
                const mobile_book::MarketBarterVolume &kr_market_barter_volume_obj) {

                PyObject* p_set_func;
                PyObject* p_args;

                p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance,
                    set_top_of_book_market_barter_volume_key.c_str());

                p_args = PyTuple_Pack(3, PyUnicode_DecodeUTF8(kr_market_barter_volume_obj.id().c_str(),
                                                              static_cast<Py_ssize_t>(kr_market_barter_volume_obj.id().size()),
                                                              nullptr),
                                      PyLong_FromLong(kr_market_barter_volume_obj.participation_period_last_barter_qty_sum()),
                                      PyLong_FromLong(kr_market_barter_volume_obj.applicable_period_seconds()));
                return PyObject_CallObject(p_set_func, p_args);
            }
        };

        class MarketDepthCache {
        public:
            static void create_bid_market_depth_cache(const std::string &kr_symbol, const int8_t id_n_position) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;

                    PyObject* p_get_mobile_book_container_object =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_symbol);

                    if (p_get_mobile_book_container_object == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_symbol);
                        return;
                    }

                    PyObject* p_set_bid_market_depth_function =
                        PyObject_GetAttrString(
                            p_get_mobile_book_container_object, mobile_book_handler::set_bid_market_depth_key.c_str());
                    PyObject* p_args = PyTuple_Pack(13, PyLong_FromLong(id_n_position + 1),
                                PyUnicode_DecodeUTF8(kr_symbol.c_str(),
                                    static_cast<Py_ssize_t>(kr_symbol.size()), nullptr),
                                Py_None, Py_None, Py_None,
                                PyLong_FromLong(id_n_position),
                                Py_None, Py_None, Py_None, Py_None, Py_None, Py_None, Py_None);
                    PyObject_CallObject(p_set_bid_market_depth_function, p_args);

                }
            }

            static void create_ask_market_depth_cache(const std::string &kr_symbol, const int8_t id_n_position) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;

                    PyObject* p_get_mobile_book_container_object =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_symbol);

                    if (p_get_mobile_book_container_object == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_symbol);
                        return;
                    }

                    PyObject* p_set_bid_market_depth_function =
                        PyObject_GetAttrString(
                            p_get_mobile_book_container_object, mobile_book_handler::set_ask_market_depth_key.c_str());
                    PyObject* p_args = PyTuple_Pack(13, PyLong_FromLong(id_n_position + 1),
                                PyUnicode_DecodeUTF8(kr_symbol.c_str(),
                                    static_cast<Py_ssize_t>(kr_symbol.size()), nullptr),
                                Py_None, Py_None, Py_None,
                                PyLong_FromLong(id_n_position),
                                Py_None, Py_None, Py_None, Py_None, Py_None, Py_None, Py_None);
                    PyObject_CallObject(p_set_bid_market_depth_function, p_args);

                }
            }

            static void* get_bid_md_mutex_from_depth(const std::string &kr_symbol, const int32_t position) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;

                    PyObject* p_get_mobile_book_container_object =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_symbol);

                    if (p_get_mobile_book_container_object == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_symbol);
                        return nullptr;
                    }

                    PyObject* p_get_md_function =
                        PyObject_GetAttrString(
                            p_get_mobile_book_container_object,
                            mobile_book_handler::get_bid_market_depth_from_depth_key.c_str());
                    PyObject* p_args = PyTuple_Pack(1, PyLong_FromLong(position));
                    PyObject* p_md_object = PyObject_CallObject(p_get_md_function, p_args);

                    if (p_md_object == Py_None) {
                        auto err = std::format("Failed to reterive market depth obj from container for symbol: {} at position: {}", kr_symbol, position);
                        LOG_ERROR_IMPL(GetLogger(), "{}", err);
                        return nullptr;
                    }

                    PyObject* p_md_mutex_func = PyObject_GetAttrString(
                        p_md_object, mobile_book_handler::get_mutex_key.c_str());
                    PyObject* p_md_mutex;
                    try {
                        p_md_mutex = PyObject_CallObject(p_md_mutex_func, nullptr);
                    } catch (std::exception& ex) {
                        auto err = std::format("Failed to reterive mutex obj from container for symbol: "
                                               "{} at position: {}, exception: {}", kr_symbol, position, ex.what());
                        LOG_ERROR_IMPL(GetLogger(), "{}", err);
                        return nullptr;
                    }
                    return PyLong_AsVoidPtr(p_md_mutex);

                }
            }

            static void* get_ask_md_mutex_from_depth(const std::string &kr_symbol, const int32_t position) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;

                    PyObject* p_get_mobile_book_container_object =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_symbol);

                    if (p_get_mobile_book_container_object == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_symbol);
                        return nullptr;
                    }

                    PyObject* p_get_md_function =
                        PyObject_GetAttrString(
                            p_get_mobile_book_container_object,
                            mobile_book_handler::get_ask_market_depth_from_depth_key.c_str());
                    PyObject* p_args = PyTuple_Pack(1, PyLong_FromLong(position));
                    PyObject* p_md_object = PyObject_CallObject(p_get_md_function, p_args);

                    if (p_md_object == Py_None) {
                        auto err = std::format("Failed to reterive market depth obj from container for symbol: {} at position: {}", kr_symbol, position);
                        LOG_ERROR_IMPL(GetLogger(), "{}", err);
                        return nullptr;
                    }
                    PyObject* p_md_mutex_func = PyObject_GetAttrString(
                        p_md_object, mobile_book_handler::get_mutex_key.c_str());
                    PyObject* p_md_mutex;
                    try {
                        p_md_mutex = PyObject_CallObject(p_md_mutex_func, nullptr);
                    } catch (std::exception& ex) {
                        auto err = std::format("Failed to reterive mutex obj from container for symbol: {} at "
                                               "position: {}, exception: {}", kr_symbol, position, ex.what());
                        LOG_ERROR_IMPL(GetLogger(), "{}", err);
                        return nullptr;
                    }
                    return PyLong_AsVoidPtr(p_md_mutex);
                }
            }

            static void update_bid_market_depth_cache(const mobile_book::MarketDepth &kr_market_depth_obj) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;

                    PyObject* p_args;
                    PyObject* p_mobile_book_container_instance =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_market_depth_obj.symbol());

                    if (p_mobile_book_container_instance == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_market_depth_obj.symbol());
                        return;
                    }

                    PyObject* p_set_market_depth_symbol = PyObject_GetAttrString(p_mobile_book_container_instance,
                        set_bid_market_depth_symbol_key.c_str());
                    PyObject* p_set_market_depth_exch_time = PyObject_GetAttrString(p_mobile_book_container_instance,
                        set_bid_market_depth_exch_time_key.c_str());
                    PyObject* p_set_market_depth_arrival_time = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_bid_market_depth_arrival_time_key.c_str());
                    PyObject* p_set_market_depth_side = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_bid_market_depth_side_key.c_str());
                    PyObject* p_set_market_depth_px = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_bid_market_depth_px_key.c_str());
                    PyObject* p_set_market_depth_qty = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_bid_market_depth_qty_key.c_str());
                    PyObject* p_set_market_depth_market_maker = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_bid_market_depth_market_maker_key.c_str());
                    PyObject* p_set_market_depth_is_smart_depth = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_bid_market_depth_is_smart_depth_key.c_str());
                    PyObject* p_set_market_depth_cumulative_notional = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_bid_market_depth_cumulative_notional_key.c_str());
                    PyObject* p_set_market_depth_cumulative_qty = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_bid_market_depth_cumulative_qty_key.c_str());
                    PyObject* p_set_market_depth_cumulative_avg_px = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_bid_market_depth_cumulative_avg_px_key.c_str());

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                     PyUnicode_DecodeUTF8(kr_market_depth_obj.symbol().c_str(),
                         static_cast<Py_ssize_t>(kr_market_depth_obj.symbol().size()), nullptr));
                    PyObject_CallObject(p_set_market_depth_symbol, p_args);

                    std::string exch_time;
                    FluxCppCore::format_time(kr_market_depth_obj.exch_time(), exch_time);
                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyUnicode_DecodeUTF8(exch_time.c_str(), static_cast<Py_ssize_t>(exch_time.size()),
                            nullptr));
                    PyObject_CallObject(p_set_market_depth_exch_time, p_args);

                    std::string arrival_time;
                    FluxCppCore::format_time(kr_market_depth_obj.arrival_time(), arrival_time);
                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyUnicode_DecodeUTF8(arrival_time.c_str(), static_cast<Py_ssize_t>(arrival_time.size()),
                            nullptr));
                    PyObject_CallObject(p_set_market_depth_arrival_time, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyUnicode_DecodeUTF8("BID", static_cast<Py_ssize_t>(std::string("BID").size()),
                            nullptr));
                    PyObject_CallObject(p_set_market_depth_side, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyFloat_FromDouble(kr_market_depth_obj.px()));
                    PyObject_CallObject(p_set_market_depth_px, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyLong_FromLong(kr_market_depth_obj.qty()));
                    PyObject_CallObject(p_set_market_depth_qty, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyUnicode_DecodeUTF8(kr_market_depth_obj.market_maker().c_str(),
                            static_cast<Py_ssize_t>(kr_market_depth_obj.market_maker().size()), nullptr));
                    PyObject_CallObject(p_set_market_depth_market_maker, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyLong_FromLong(kr_market_depth_obj.is_smart_depth()));
                    PyObject_CallObject(p_set_market_depth_is_smart_depth, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyFloat_FromDouble(kr_market_depth_obj.cumulative_notional()));
                    PyObject_CallObject(p_set_market_depth_cumulative_notional, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyLong_FromLong(kr_market_depth_obj.cumulative_qty()));
                    PyObject_CallObject(p_set_market_depth_cumulative_qty, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyFloat_FromDouble(kr_market_depth_obj.cumulative_avg_px()));
                    PyObject_CallObject(p_set_market_depth_cumulative_avg_px, p_args);
                }

            }

            static void update_ask_market_depth_cache(const mobile_book::MarketDepth &kr_market_depth_obj) {
                Py_Initialize();

                {
                    FluxCppCore::PythonGIL gil;
                    PyObject* p_mobile_book_container_instance =
                        FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(
                            kr_market_depth_obj.symbol());

                    PyObject* p_args;
                    if (p_mobile_book_container_instance == Py_None) {
                        LOG_ERROR_IMPL(GetLogger(), "Symbol: {} not found in the container obj",
                            kr_market_depth_obj.symbol());
                        return;
                    }

                    PyObject* p_set_market_depth_symbol = PyObject_GetAttrString(p_mobile_book_container_instance,
                        set_ask_market_depth_symbol_key.c_str());
                    PyObject* p_set_market_depth_exch_time = PyObject_GetAttrString(p_mobile_book_container_instance,
                        set_ask_market_depth_exch_time_key.c_str());
                    PyObject* p_set_market_depth_arrival_time = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_ask_market_depth_arrival_time_key.c_str());
                    PyObject* p_set_market_depth_side = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_ask_market_depth_side_key.c_str());
                    PyObject* p_set_market_depth_px = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_ask_market_depth_px_key.c_str());
                    PyObject* p_set_market_depth_qty = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_ask_market_depth_qty_key.c_str());
                    PyObject* p_set_market_depth_market_maker = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_ask_market_depth_market_maker_key.c_str());
                    PyObject* p_set_market_depth_is_smart_depth = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_ask_market_depth_is_smart_depth_key.c_str());
                    PyObject* p_set_market_depth_cumulative_notional = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_ask_market_depth_cumulative_notional_key.c_str());
                    PyObject* p_set_market_depth_cumulative_qty = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_ask_market_depth_cumulative_qty_key.c_str());
                    PyObject* p_set_market_depth_cumulative_avg_px = PyObject_GetAttrString(p_mobile_book_container_instance,
                         set_ask_market_depth_cumulative_avg_px_key.c_str());

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                     PyUnicode_DecodeUTF8(kr_market_depth_obj.symbol().c_str(),
                         static_cast<Py_ssize_t>(kr_market_depth_obj.symbol().size()), nullptr));
                    PyObject_CallObject(p_set_market_depth_symbol, p_args);

                    std::string exch_time;
                    FluxCppCore::format_time(kr_market_depth_obj.exch_time(), exch_time);
                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyUnicode_DecodeUTF8(exch_time.c_str(), static_cast<Py_ssize_t>(exch_time.size()),
                            nullptr));
                    PyObject_CallObject(p_set_market_depth_exch_time, p_args);

                    std::string arrival_time;
                    FluxCppCore::format_time(kr_market_depth_obj.arrival_time(), arrival_time);
                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyUnicode_DecodeUTF8(arrival_time.c_str(), static_cast<Py_ssize_t>(arrival_time.size()),
                            nullptr));
                    PyObject_CallObject(p_set_market_depth_arrival_time, p_args);
                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyUnicode_DecodeUTF8("ASK", static_cast<Py_ssize_t>(std::string("ASK").size()),
                            nullptr));
                    PyObject_CallObject(p_set_market_depth_side, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyFloat_FromDouble(kr_market_depth_obj.px()));
                    PyObject_CallObject(p_set_market_depth_px, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyLong_FromLong(kr_market_depth_obj.qty()));
                    PyObject_CallObject(p_set_market_depth_qty, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyUnicode_DecodeUTF8(kr_market_depth_obj.market_maker().c_str(),
                            static_cast<Py_ssize_t>(kr_market_depth_obj.market_maker().size()), nullptr));
                    PyObject_CallObject(p_set_market_depth_market_maker, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyLong_FromLong(kr_market_depth_obj.is_smart_depth()));
                    PyObject_CallObject(p_set_market_depth_is_smart_depth, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyFloat_FromDouble(kr_market_depth_obj.cumulative_notional()));
                    PyObject_CallObject(p_set_market_depth_cumulative_notional, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyLong_FromLong(kr_market_depth_obj.cumulative_qty()));
                    PyObject_CallObject(p_set_market_depth_cumulative_qty, p_args);

                    p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()),
                        PyFloat_FromDouble(kr_market_depth_obj.cumulative_avg_px()));
                    PyObject_CallObject(p_set_market_depth_cumulative_avg_px, p_args);

                }

            }
        };
    }
}

