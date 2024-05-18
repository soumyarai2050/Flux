#pragma once

#include <iostream>
#include <Python.h>

#include "mobile_book_service.pb.h"
#include "utility_functions.h"
#include "string_util.h"


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


namespace mobile_book_cache {
    using namespace mobile_book_handler;
    using namespace FluxCppCore;
    class MarketDepthCache {

    public:

        void update_or_create_market_depth_cache(const mobile_book::MarketDepth &kr_market_depth_obj) {
            Py_Initialize();
	        {

                FluxCppCore::PythonGIL gil;

                PyObject* p_mobile_book_container_instance = nullptr;
                PyObject* p_market_depth_instance = nullptr;
                PyObject* p_set_func = nullptr;
                PyObject* p_args = nullptr;
                PyObject* p_mutex = nullptr;

                p_mobile_book_container_instance = FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(kr_market_depth_obj.symbol());
                if (!p_mobile_book_container_instance) {

                    FluxCppCore::AddOrGetContainerObj::add_container_obj_for_symbol(kr_market_depth_obj.symbol());

                    p_mobile_book_container_instance = FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(kr_market_depth_obj.symbol());
                    create_market_depth_cache(kr_market_depth_obj, p_mobile_book_container_instance);

                } else {

                    if (kr_market_depth_obj.side() == mobile_book::TickType::BID) {
                            PyObject* p_get_bid_market_depth_from_depth = PyObject_GetAttrString(p_mobile_book_container_instance, get_bid_market_depth_from_depth_key.c_str());
                            assert(p_get_bid_market_depth_from_depth != nullptr);

                            p_args = PyTuple_Pack(1, PyLong_FromLong(kr_market_depth_obj.position()));
                            p_market_depth_instance = PyObject_CallObject(p_get_bid_market_depth_from_depth, p_args);
                            if (p_market_depth_instance == Py_None) {
                                create_market_depth_cache(kr_market_depth_obj, p_mobile_book_container_instance);
                            } else {
                                const std::string time_str = PyUnicode_AsUTF8(PyObject_Str(PyObject_GetAttrString(p_market_depth_instance, "exch_time")));
                                FluxCppCore::TimeComparison time = FluxCppCore::StringUtil::find_latest_time(time_str,
                                                                                                             kr_market_depth_obj.exch_time());
                                p_set_func = PyObject_GetAttrString(p_market_depth_instance, get_mutex_key.c_str());
                                p_mutex = PyObject_CallObject(p_set_func, nullptr);
                                if(time == FluxCppCore::TimeComparison::TIME2_LATER or time == FluxCppCore::TimeComparison::BOTH_EQUAL) {
                                    update_bid_market_depth_cache(kr_market_depth_obj, p_mobile_book_container_instance, p_mutex);
                                }
                                // update_bid_market_depth_cache(kr_market_depth_obj, p_mobile_book_container_instance, p_mutex);
                            }


                    } else {
                            PyObject* p_get_ask_market_depth_from_depth = PyObject_GetAttrString(p_mobile_book_container_instance, get_ask_market_depth_from_depth_key.c_str());
                            assert(p_get_ask_market_depth_from_depth != nullptr);

                            p_args = PyTuple_Pack(1, PyLong_FromLong(kr_market_depth_obj.position()));
                            p_market_depth_instance = PyObject_CallObject(p_get_ask_market_depth_from_depth, p_args);
                            if (p_market_depth_instance == Py_None) {
                                create_market_depth_cache(kr_market_depth_obj, p_mobile_book_container_instance);
                            } else {
                                const std::string time_str = PyUnicode_AsUTF8(PyObject_Str(PyObject_GetAttrString(p_market_depth_instance, "exch_time")));
                                FluxCppCore::TimeComparison time = FluxCppCore::StringUtil::find_latest_time(time_str,
                                                                                                             kr_market_depth_obj.exch_time());
                                p_set_func = PyObject_GetAttrString(p_market_depth_instance, get_mutex_key.c_str());
                                p_mutex = PyObject_CallObject(p_set_func, nullptr);
                                if (time == FluxCppCore::TimeComparison::TIME2_LATER or time == FluxCppCore::TimeComparison::BOTH_EQUAL) {
                                    update_ask_market_depth_cache(kr_market_depth_obj, p_mobile_book_container_instance, p_mutex);
                                }
                                // update_ask_market_depth_cache(kr_market_depth_obj, p_mobile_book_container_instance, p_mutex);
                            }
                    }

                }

	        }

        }

    protected:

        void create_market_depth_cache(const mobile_book::MarketDepth &kr_market_depth_obj, PyObject* p_mobile_book_container_instance) {
            PyObject* p_set_func = nullptr;
            PyObject* p_args = nullptr;
            const char* set_func_name = nullptr; // Declare outside the if-else blocks

            if (kr_market_depth_obj.side() == mobile_book::TickType::BID) {
                set_func_name = "set_bid_market_depth"; // Update the existing variable
            } else if (kr_market_depth_obj.side() == mobile_book::TickType::ASK) {
                set_func_name = "set_ask_market_depth"; // Update the existing variable
            }

            p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, set_func_name);
            p_args = FluxCppCore::MessageTypeToPythonArgs::message_type_to_python_args(kr_market_depth_obj);
            assert(PyObject_IsTrue(PyObject_CallObject(p_set_func, p_args)));
        }

        void update_bid_market_depth_cache(const mobile_book::MarketDepth &kr_market_depth_obj, PyObject* p_mobile_book_container_instance,
                                           PyObject* p_mutex) {

            PyObject* p_args = nullptr;

            // TODO: seperate 2 methods for bid and ask to avoid nested if-else
            PyObject* p_set_market_depth_symbol = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_symbol_key.c_str());
            PyObject* p_set_market_depth_exch_time = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_exch_time_key.c_str());
            PyObject* p_set_market_depth_arrival_time = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_arrival_time_key.c_str());
            PyObject* p_set_market_depth_side = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_side_key.c_str());
            PyObject* p_set_market_depth_px = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_px_key.c_str());
            PyObject* p_set_market_depth_qty = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_qty_key.c_str());
            PyObject* p_set_market_depth_market_maker = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_market_maker_key.c_str());
            PyObject* p_set_market_depth_is_smart_depth = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_is_smart_depth_key.c_str());
            PyObject* p_set_market_depth_cumulative_notional = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_cumulative_notional_key.c_str());
            PyObject* p_set_market_depth_cumulative_qty = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_cumulative_qty_key.c_str());
            PyObject* p_set_market_depth_cumulative_avg_px = PyObject_GetAttrString(p_mobile_book_container_instance, set_bid_market_depth_cumulative_avg_px_key.c_str());

            assert(p_set_market_depth_symbol != nullptr &&
                   p_set_market_depth_exch_time != nullptr &&
                   p_set_market_depth_arrival_time != nullptr &&
                   p_set_market_depth_side != nullptr &&
                   p_set_market_depth_px != nullptr &&
                   p_set_market_depth_qty != nullptr &&
                   p_set_market_depth_market_maker != nullptr &&
                   p_set_market_depth_is_smart_depth != nullptr &&
                   p_set_market_depth_cumulative_notional != nullptr &&
                   p_set_market_depth_cumulative_qty != nullptr &&
                   p_set_market_depth_cumulative_avg_px != nullptr);
            // p_mutex= init_mutex();
            void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
            std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);

            {
                // std::lock_guard<std::mutex> lock(*lock_mutex);
                std::unique_lock<std::mutex> lock(*lock_mutex, std::try_to_lock_t{});
                if (!lock.owns_lock()) {
                    return;
                }

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyUnicode_DecodeUTF8(kr_market_depth_obj.symbol().c_str(), static_cast<Py_ssize_t>(kr_market_depth_obj.symbol().size()), nullptr));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_symbol, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyUnicode_DecodeUTF8(kr_market_depth_obj.exch_time().c_str(), static_cast<Py_ssize_t>(kr_market_depth_obj.exch_time().size()), nullptr));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_exch_time, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyUnicode_DecodeUTF8(kr_market_depth_obj.arrival_time().c_str(), static_cast<Py_ssize_t>(kr_market_depth_obj.arrival_time().size()), nullptr));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_arrival_time, p_args)));

                // p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyUnicode_DecodeUTF8("BID", static_cast<Py_ssize_t>(std::string("BID").size()), nullptr));
                // assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_side, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyFloat_FromDouble(kr_market_depth_obj.px()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_px, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyLong_FromLong(kr_market_depth_obj.qty()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_qty, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyUnicode_DecodeUTF8(kr_market_depth_obj.market_maker().c_str(), static_cast<Py_ssize_t>(kr_market_depth_obj.market_maker().size()), nullptr));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_market_maker, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyLong_FromLong(kr_market_depth_obj.is_smart_depth()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_is_smart_depth, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyFloat_FromDouble(kr_market_depth_obj.cumulative_notional()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_cumulative_notional, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyLong_FromLong(kr_market_depth_obj.cumulative_qty()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_cumulative_qty, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyFloat_FromDouble(kr_market_depth_obj.cumulative_avg_px()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_cumulative_avg_px, p_args)));
            }
        }

        void update_ask_market_depth_cache(const mobile_book::MarketDepth &kr_market_depth_obj, PyObject* p_mobile_book_container_instance,
                                           PyObject* p_mutex) {

            PyObject* p_args = nullptr;

            PyObject* p_set_market_depth_symbol = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_symbol_key.c_str());
            PyObject* p_set_market_depth_exch_time = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_exch_time_key.c_str());
            PyObject* p_set_market_depth_arrival_time = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_arrival_time_key.c_str());
            PyObject* p_set_market_depth_side = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_side_key.c_str());
            PyObject* p_set_market_depth_px = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_px_key.c_str());
            PyObject* p_set_market_depth_qty = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_qty_key.c_str());
            PyObject* p_set_market_depth_market_maker = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_market_maker_key.c_str());
            PyObject* p_set_market_depth_is_smart_depth = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_is_smart_depth_key.c_str());
            PyObject* p_set_market_depth_cumulative_notional = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_cumulative_notional_key.c_str());
            PyObject* p_set_market_depth_cumulative_qty = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_cumulative_qty_key.c_str());
            PyObject* p_set_market_depth_cumulative_avg_px = PyObject_GetAttrString(p_mobile_book_container_instance, set_ask_market_depth_cumulative_avg_px_key.c_str());

            assert(p_set_market_depth_symbol != nullptr &&
                   p_set_market_depth_exch_time != nullptr &&
                   p_set_market_depth_arrival_time != nullptr &&
                   p_set_market_depth_side != nullptr &&
                   p_set_market_depth_px != nullptr &&
                   p_set_market_depth_qty != nullptr &&
                   p_set_market_depth_market_maker != nullptr &&
                   p_set_market_depth_is_smart_depth != nullptr &&
                   p_set_market_depth_cumulative_notional != nullptr &&
                   p_set_market_depth_cumulative_qty != nullptr &&
                   p_set_market_depth_cumulative_avg_px != nullptr);

            void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
            std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);

            {
                // std::lock_guard<std::mutex> lock(*lock_mutex);
                std::unique_lock<std::mutex> lock(*lock_mutex, std::try_to_lock_t{});
                if (!lock.owns_lock()) {
                    return;
                }

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyUnicode_DecodeUTF8(kr_market_depth_obj.symbol().c_str(), static_cast<Py_ssize_t>(kr_market_depth_obj.symbol().size()), nullptr));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_symbol, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyUnicode_DecodeUTF8(kr_market_depth_obj.exch_time().c_str(), static_cast<Py_ssize_t>(kr_market_depth_obj.exch_time().size()), nullptr));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_exch_time, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyUnicode_DecodeUTF8(kr_market_depth_obj.arrival_time().c_str(), static_cast<Py_ssize_t>(kr_market_depth_obj.arrival_time().size()), nullptr));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_arrival_time, p_args)));

                // p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyUnicode_DecodeUTF8("ASK", static_cast<Py_ssize_t>(std::string("ASK").size()), nullptr));
                // assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_side, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyFloat_FromDouble(kr_market_depth_obj.px()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_px, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyLong_FromLong(kr_market_depth_obj.qty()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_qty, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyUnicode_DecodeUTF8(kr_market_depth_obj.market_maker().c_str(), static_cast<Py_ssize_t>(kr_market_depth_obj.market_maker().size()), nullptr));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_market_maker, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyLong_FromLong(kr_market_depth_obj.is_smart_depth()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_is_smart_depth, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyFloat_FromDouble(kr_market_depth_obj.cumulative_notional()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_cumulative_notional, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyLong_FromLong(kr_market_depth_obj.cumulative_qty()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_cumulative_qty, p_args)));

                p_args = PyTuple_Pack(2, PyLong_FromLong(kr_market_depth_obj.position()), PyFloat_FromDouble(kr_market_depth_obj.cumulative_avg_px()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_market_depth_cumulative_avg_px, p_args)));
            }
        }

    };

    class LastBarterCache {

    public:

        void update_or_create_last_barter_cache(const mobile_book::LastBarter &kr_last_barter_obj) {
		    Py_Initialize();

            PyObject* p_mobile_book_container_instance = nullptr;
            PyObject* p_module = nullptr;
            PyObject* p_set_func = nullptr;
            PyObject* p_last_barter_instance = nullptr;
            PyObject* p_mutex = nullptr;
            PyObject* mp_market_barter_vol_class_ = nullptr;

		    {
                FluxCppCore::PythonGIL gil;

                p_module = PyImport_ImportModule(mobile_book_cache_module_name.c_str());
                assert(p_module != nullptr);
                mp_market_barter_vol_class_ = PyObject_GetAttrString(p_module, mobile_book_handler::market_barter_volume_msg_name.c_str());
                assert(mp_market_barter_vol_class_ != nullptr);

                p_mobile_book_container_instance = FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(kr_last_barter_obj.symbol_n_exch_id().symbol());
                if (!p_mobile_book_container_instance) {
                    FluxCppCore::AddOrGetContainerObj::add_container_obj_for_symbol(kr_last_barter_obj.symbol_n_exch_id().symbol());

                    p_mobile_book_container_instance = FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(kr_last_barter_obj.symbol_n_exch_id().symbol());

                    create_last_barter_cache(kr_last_barter_obj, p_mobile_book_container_instance, mp_market_barter_vol_class_);

                } else {

                    assert(p_mobile_book_container_instance != nullptr);
                    p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, get_last_barter_key.c_str());
                    p_last_barter_instance = PyObject_CallObject(p_set_func, nullptr);

                    if (p_last_barter_instance == Py_None) {
                        create_last_barter_cache(kr_last_barter_obj, p_mobile_book_container_instance, mp_market_barter_vol_class_);
                    } else {
                        assert(p_last_barter_instance != Py_None);
                        p_set_func = PyObject_GetAttrString(p_last_barter_instance, get_mutex_key.c_str());
                        if (!p_set_func or PyCallable_Check(p_set_func)) {
                            PyErr_Print();
                        }
                        p_mutex = PyObject_CallObject(p_set_func, nullptr);
                        const std::string time_str = PyUnicode_AsUTF8(PyObject_Str(PyObject_GetAttrString(p_last_barter_instance, "exch_time")));
                        FluxCppCore::TimeComparison time = FluxCppCore::StringUtil::find_latest_time(time_str,
                                                                                                     kr_last_barter_obj.exch_time());
                        if (time == FluxCppCore::TimeComparison::TIME2_LATER or time == FluxCppCore::TimeComparison::BOTH_EQUAL) {
                            update_last_barter_cache(kr_last_barter_obj, p_mobile_book_container_instance, p_mutex);
                        }
                        // update_last_barter_cache(kr_last_barter_obj, p_mobile_book_container_instance, p_mutex);
                    }
                }
		    }
        }

    protected:

        void create_last_barter_cache(const mobile_book::LastBarter &kr_last_barter_obj, PyObject* p_mobile_book_container_instance,
                                     PyObject* mp_market_barter_vol_class_) {
            PyObject* p_set_func = nullptr;
            PyObject* p_market_barter_volume_args = nullptr;
            PyObject* p_market_barter_volume_instance = nullptr;
            PyObject* p_args = nullptr;

            p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, set_last_barter_key.c_str());
            p_market_barter_volume_args = PyTuple_Pack(3, PyUnicode_DecodeUTF8(kr_last_barter_obj.market_barter_volume().id().c_str(),
                                                                              static_cast<Py_ssize_t>(kr_last_barter_obj.market_barter_volume().id().size()),
                                                                              nullptr),
                                                      PyLong_FromLong(kr_last_barter_obj.market_barter_volume().participation_period_last_barter_qty_sum()),
                                                      PyLong_FromLong(kr_last_barter_obj.market_barter_volume().applicable_period_seconds()));
            p_market_barter_volume_instance = PyObject_CallObject(mp_market_barter_vol_class_, p_market_barter_volume_args);

            p_args = FluxCppCore::MessageTypeToPythonArgs::message_type_to_python_args(kr_last_barter_obj, p_market_barter_volume_instance);

            assert(Py_IsTrue(PyObject_CallObject(p_set_func, p_args)));
        }

        void update_last_barter_cache(const mobile_book::LastBarter &kr_last_barter_obj, PyObject* p_mobile_book_container_instance,
                                     PyObject* p_mutex) {

            PyObject* p_args = nullptr;
            void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
            std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);

            PyObject* p_set_last_barter_exch_id = PyObject_GetAttrString(p_mobile_book_container_instance, set_last_barter_exch_id_key.c_str());
            PyObject* p_set_last_barter_exch_time = PyObject_GetAttrString(p_mobile_book_container_instance, set_last_barter_exch_time_key.c_str());
            PyObject* p_set_last_barter_arrival_time = PyObject_GetAttrString(p_mobile_book_container_instance, set_last_barter_arrival_time_key.c_str());
            PyObject* p_set_last_barter_px = PyObject_GetAttrString(p_mobile_book_container_instance, set_last_barter_px_key.c_str());
            PyObject* p_set_last_barter_qty = PyObject_GetAttrString(p_mobile_book_container_instance, set_last_barter_qty_key.c_str());
            PyObject* p_set_last_barter_premium = PyObject_GetAttrString(p_mobile_book_container_instance, set_last_barter_premium_key.c_str());
            PyObject* p_set_last_barter_market_barter_volume_participation_period_last_barter_qty_sum =
                    PyObject_GetAttrString(p_mobile_book_container_instance,
                                           set_last_barter_market_barter_volume_participation_period_last_barter_qty_sum_key.c_str());
            PyObject* p_set_last_barter_market_barter_volume_applicable_period_seconds =
                    PyObject_GetAttrString(p_mobile_book_container_instance,
                                           set_last_barter_market_barter_volume_applicable_period_seconds_key.c_str());
            assert(p_set_last_barter_exch_id != nullptr && p_set_last_barter_exch_time != nullptr &&
                   p_set_last_barter_arrival_time != nullptr && p_set_last_barter_px != nullptr &&
                   p_set_last_barter_qty != nullptr && p_set_last_barter_premium != nullptr &&
                   p_set_last_barter_market_barter_volume_participation_period_last_barter_qty_sum != nullptr &&
                   p_set_last_barter_market_barter_volume_applicable_period_seconds != nullptr);

            try {
                // std::lock_guard<std::mutex> lock(*lock_mutex);
                std::unique_lock<std::mutex> lock(*lock_mutex, std::try_to_lock_t{});
                if (!lock.owns_lock()) {
                    return;
                }

                p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_last_barter_obj.symbol_n_exch_id().exch_id().c_str(),
                                                              static_cast<Py_ssize_t>(kr_last_barter_obj.symbol_n_exch_id().exch_id().size()),
                                                              nullptr));
                assert(Py_IsTrue(PyObject_CallObject(p_set_last_barter_exch_id, p_args)));


                p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_last_barter_obj.exch_time().c_str(),
                                                              static_cast<Py_ssize_t>(kr_last_barter_obj.exch_time().size()),
                                                              nullptr));
                assert(Py_IsTrue(PyObject_CallObject(p_set_last_barter_exch_time, p_args)));

                p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_last_barter_obj.arrival_time().c_str(),
                                                              static_cast<Py_ssize_t>(kr_last_barter_obj.arrival_time().size()),
                                                              nullptr));
                assert(Py_IsTrue(PyObject_CallObject(p_set_last_barter_arrival_time, p_args)));

                p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_last_barter_obj.px()));
                assert(Py_IsTrue(PyObject_CallObject(p_set_last_barter_px, p_args)));

                p_args = PyTuple_Pack(1, PyLong_FromLong(kr_last_barter_obj.qty()));
                assert(Py_IsTrue(PyObject_CallObject(p_set_last_barter_qty, p_args)));

                p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_last_barter_obj.premium()));
                assert(Py_IsTrue(PyObject_CallObject(p_set_last_barter_premium, p_args)));

                p_args = PyTuple_Pack(1, PyLong_FromLong(kr_last_barter_obj.market_barter_volume().participation_period_last_barter_qty_sum()));
                assert(Py_IsTrue(PyObject_CallObject(p_set_last_barter_market_barter_volume_participation_period_last_barter_qty_sum, p_args)));

                p_args = PyTuple_Pack(1, PyLong_FromLong(kr_last_barter_obj.market_barter_volume().applicable_period_seconds()));
                assert(Py_IsTrue(PyObject_CallObject(p_set_last_barter_market_barter_volume_applicable_period_seconds, p_args)));

            } catch (std::exception& exception) {
                std::cerr << "Exception caught: " << exception.what() << std::endl;
            }
        }


    };

    class TopOfBookCache {

    public:
        void update_or_create_top_of_book_cache(const mobile_book::TopOfBook &kr_top_of_book, const std::string &kr_side) {
		Py_Initialize();
		{
            FluxCppCore::PythonGIL gil;

            PyObject* p_mobile_book_container_instance = nullptr;
            PyObject* p_module = nullptr;
            PyObject* p_set_func = nullptr;
            PyObject* p_market_barter_volume_class = nullptr;
            PyObject* p_top_of_book_instance = nullptr;
            PyObject* p_mutex = nullptr;

            p_module = PyImport_ImportModule(mobile_book_cache_key.c_str());
            assert(p_module != nullptr);

            p_mobile_book_container_instance = FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(kr_top_of_book.symbol());
            p_market_barter_volume_class = PyObject_GetAttrString(p_module, market_barter_volume_msg_name.c_str());
            assert(p_market_barter_volume_class != nullptr);

            if (!p_mobile_book_container_instance) {

                FluxCppCore::AddOrGetContainerObj::add_container_obj_for_symbol(kr_top_of_book.symbol());
                p_mobile_book_container_instance = FluxCppCore::AddOrGetContainerObj::get_mobile_book_container_instance(kr_top_of_book.symbol());

                create_top_of_book_cache(kr_top_of_book, p_mobile_book_container_instance, p_market_barter_volume_class);
            } else {
                p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, get_top_of_book_key.c_str());
                p_top_of_book_instance = PyObject_CallObject(p_set_func, nullptr);

                if (p_top_of_book_instance == Py_None) {
                    create_top_of_book_cache(kr_top_of_book, p_mobile_book_container_instance, p_market_barter_volume_class);
                } else {
                    // kr_top_of_book.has_bid_quote()
                    p_set_func = PyObject_GetAttrString(p_top_of_book_instance, get_mutex_key.c_str());
                    p_mutex = PyObject_CallObject(p_set_func, nullptr);
                    const std::string time_str = PyUnicode_AsUTF8(PyObject_Str(PyObject_GetAttrString(p_top_of_book_instance, "last_update_date_time")));
                    FluxCppCore::TimeComparison time = FluxCppCore::StringUtil::find_latest_time(time_str,
                            kr_top_of_book.last_update_date_time());

                    if (kr_side == "BID") {

                        PyObject* p_get_top_of_book_bid_quote = PyObject_GetAttrString(p_mobile_book_container_instance, get_top_of_book_bid_quote_key.c_str());
                        PyObject* p_last_update_date_time = PyObject_GetAttrString(p_top_of_book_instance, "last_update_date_time");

                        assert(p_get_top_of_book_bid_quote != nullptr);

                        if (PyObject_CallObject(p_get_top_of_book_bid_quote, nullptr) == Py_None) {
                            create_top_of_book_bid_quote(kr_top_of_book, p_mobile_book_container_instance);
                        } else {
                            if (time == FluxCppCore::TimeComparison::TIME2_LATER or time == FluxCppCore::TimeComparison::BOTH_EQUAL) {
                                update_top_of_book_bid_quote(kr_top_of_book, p_mobile_book_container_instance, p_mutex);
                            }
                            // update_top_of_book_bid_quote(kr_top_of_book, p_mobile_book_container_instance, p_mutex);
                        }


                    } else if (kr_side == "ASK") {

                        PyObject* p_get_top_of_book_ask_quote = PyObject_GetAttrString(p_mobile_book_container_instance, get_top_of_book_ask_quote_key.c_str());
                        assert(p_get_top_of_book_ask_quote != nullptr);

                        if (PyObject_CallObject(p_get_top_of_book_ask_quote, nullptr) == Py_None) {
                            create_top_of_book_ask_quote(kr_top_of_book, p_mobile_book_container_instance);
                        } else {
                            if (time == FluxCppCore::TimeComparison::TIME2_LATER or time == FluxCppCore::TimeComparison::BOTH_EQUAL) {
                                update_top_of_book_ask_quote(kr_top_of_book, p_mobile_book_container_instance, p_mutex);
                            }
                            // update_top_of_book_ask_quote(kr_top_of_book, p_mobile_book_container_instance, p_mutex);
                        }

                    } else {

                        PyObject* p_get_top_of_book_last_barter = PyObject_GetAttrString(p_mobile_book_container_instance, get_top_of_book_last_barter_key.c_str());
                        // std::cout << "Time: "  << std::endl;

                        assert(p_get_top_of_book_last_barter != nullptr);

                        if (PyObject_CallObject(p_get_top_of_book_last_barter, nullptr) == Py_None) {
                            create_top_of_book_last_barter(kr_top_of_book, p_mobile_book_container_instance);
                        } else {
                            if (time == FluxCppCore::TimeComparison::TIME2_LATER or time == FluxCppCore::TimeComparison::BOTH_EQUAL) {
                                update_top_of_book_last_barter(kr_top_of_book, p_mobile_book_container_instance, p_mutex);
                            }
                            // update_top_of_book_last_barter(kr_top_of_book, p_mobile_book_container_instance, p_mutex);
                        }

                    }

                    // if (time == FluxCppCore::TimeComparison::TIME1_LATER) {
                    //     update_top_of_book_top_lev_fld(kr_top_of_book, p_mobile_book_container_instance, p_mutex);
                    // }
//                    update_top_of_book_top_lev_fld(kr_top_of_book, p_mobile_book_container_instance, p_mutex);
                }
            }
		}

        }

    protected:

        void create_top_of_book_cache(const mobile_book::TopOfBook &kr_top_of_book, PyObject* p_mobile_book_container_instance,
                                      PyObject* mp_market_barter_vol_class_) {
            PyObject* p_set_func = nullptr;
            PyObject* p_market_barter_volume_list = nullptr;
            PyObject* p_args = nullptr;
            PyObject* p_market_barter_volume_instance = nullptr;

            p_market_barter_volume_list = PyList_New(0);
            p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_key.c_str());
            for (int i = 0; i < kr_top_of_book.market_barter_volume_size(); ++i) {
                p_args = FluxCppCore::MessageTypeToPythonArgs::message_type_to_python_args(kr_top_of_book.market_barter_volume(i));
                p_market_barter_volume_instance = PyObject_CallObject(mp_market_barter_vol_class_, p_args);
                assert(p_market_barter_volume_instance != nullptr);
                PyList_Append(p_market_barter_volume_list, p_market_barter_volume_instance);
            }
            p_args = FluxCppCore::MessageTypeToPythonArgs::message_type_to_python_args(kr_top_of_book, p_market_barter_volume_list);

            assert(PyObject_IsTrue(PyObject_CallObject(p_set_func, p_args)));
        }

        void create_top_of_book_bid_quote(const mobile_book::TopOfBook &kr_top_of_book_obj, PyObject* p_mobile_book_container_instance) {
            PyObject* p_args = nullptr;

            PyObject* p_set_top_of_book_bid_quote = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_bid_quote_key.c_str());
            assert(p_set_top_of_book_bid_quote != nullptr);
            p_args = FluxCppCore::MessageTypeToPythonArgs::message_type_to_python_args(kr_top_of_book_obj.bid_quote());
            assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_bid_quote, p_args)));

        }

        void update_top_of_book_bid_quote(const mobile_book::TopOfBook &kr_top_book_obj, PyObject* p_mobile_book_container_instance,
                                          PyObject* p_mutex) {

            PyObject* p_args = nullptr;
            void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
            std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);

            PyObject* p_set_top_of_book_price = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_bid_quote_px_key.c_str());
            PyObject* p_set_top_of_book_qty = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_bid_quote_qty_key.c_str());
            PyObject* p_set_top_of_book_premium = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_bid_quote_premium_key.c_str());
            PyObject* p_set_top_of_book_bid_quote_last_update_date_time  =
                    PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_bid_quote_last_update_date_time_key.c_str());

            assert(p_set_top_of_book_price != nullptr and
                   p_set_top_of_book_qty != nullptr and p_set_top_of_book_premium != nullptr and
                           p_set_top_of_book_bid_quote_last_update_date_time != nullptr);

            try {

                // std::lock_guard<std::mutex> lock(*lock_mutex);
                std::unique_lock<std::mutex> lock(*lock_mutex, std::try_to_lock_t{});

                if (!lock.owns_lock())
                {return;}

                p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_book_obj.bid_quote().px()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_price, p_args)));

                p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_book_obj.bid_quote().qty()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_qty, p_args)));

                p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_book_obj.bid_quote().premium()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_premium, p_args)));

                p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(
                        kr_top_book_obj.bid_quote().last_update_date_time().c_str(),
                        static_cast<Py_ssize_t>(kr_top_book_obj.bid_quote().last_update_date_time().size()),
                        nullptr));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_bid_quote_last_update_date_time, p_args)));
                update_top_of_book_top_lev_fld(kr_top_book_obj, p_mobile_book_container_instance, p_mutex);

            } catch (std::exception& exception) {
                std::cerr << "Exception caught: " << exception.what() << std::endl;
            }
        }

        void create_top_of_book_ask_quote(const mobile_book::TopOfBook &kr_top_of_book_obj, PyObject* p_mobile_book_container_instance) {

            PyObject* p_args = nullptr;

            PyObject* p_set_top_of_book_ask_quote = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_ask_quote_key.c_str());
            assert(p_set_top_of_book_ask_quote != nullptr);
            p_args = FluxCppCore::MessageTypeToPythonArgs::message_type_to_python_args(kr_top_of_book_obj.ask_quote());
            assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_ask_quote, p_args)));

        }

        void update_top_of_book_ask_quote(const mobile_book::TopOfBook &kr_top_of_book_obj, PyObject* p_mobile_book_container_instance,
                                          PyObject* p_mutex) {

            PyObject* p_set_top_of_book_price = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_ask_quote_px_key.c_str());
            PyObject* p_set_top_of_book_qty = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_ask_quote_qty_key.c_str());
            PyObject* p_set_top_of_book_premium = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_ask_quote_premium_key.c_str());
            PyObject* p_set_top_of_book_ask_quote_last_update_date_time =
                    PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_ask_quote_last_update_date_time_key.c_str());

            assert(p_set_top_of_book_price != nullptr and
                   p_set_top_of_book_qty != nullptr and p_set_top_of_book_premium != nullptr and
                   p_set_top_of_book_ask_quote_last_update_date_time != nullptr);

            PyObject* p_args = nullptr;
            void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
            std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);

            try {

                // std::lock_guard<std::mutex> lock(*lock_mutex);
                std::unique_lock<std::mutex> lock(*lock_mutex, std::try_to_lock_t{});
                if (!lock.owns_lock()) {
                    std::cout << "lock not found" << std::endl;
                    return;
                }

                p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book_obj.ask_quote().px()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_price, p_args)));

                p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_of_book_obj.ask_quote().qty()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_qty, p_args)));

                p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book_obj.ask_quote().premium()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_premium, p_args)));

                p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(
                        kr_top_of_book_obj.ask_quote().last_update_date_time().c_str(),
                        static_cast<Py_ssize_t>(kr_top_of_book_obj.ask_quote().last_update_date_time().size()),
                        nullptr));
                assert(PyObject_IsTrue(
                        PyObject_CallObject(p_set_top_of_book_ask_quote_last_update_date_time, p_args)));
                update_top_of_book_top_lev_fld(kr_top_of_book_obj, p_mobile_book_container_instance, p_mutex);
            } catch (std::exception &exception) {
                std::cerr << "Exception caught: " << exception.what() << std::endl;
            }
        }

        void create_top_of_book_last_barter(const mobile_book::TopOfBook &kr_top_of_book_obj, PyObject* p_mobile_book_container_instance) {

            PyObject* p_args = nullptr;
            PyObject* p_set_top_of_book_last_barter = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_last_barter_key.c_str());
            assert(p_set_top_of_book_last_barter != nullptr);
            p_args = FluxCppCore::MessageTypeToPythonArgs::message_type_to_python_args(kr_top_of_book_obj.last_barter());
            assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_last_barter, p_args)));
        }

        void update_top_of_book_last_barter(const mobile_book::TopOfBook &kr_top_of_book_obj, PyObject* p_mobile_book_container_instance,
                                           PyObject* p_mutex) {

            PyObject* p_set_top_of_book_price = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_last_barter_px_key.c_str());
            PyObject* p_set_top_of_book_qty = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_last_barter_qty_key.c_str());
            PyObject* p_set_top_of_book_premium = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_last_barter_premium_key.c_str());
            PyObject* p_set_top_of_book_last_barter_last_update_date_time =
                    PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_last_barter_last_update_date_time_key.c_str());

            assert( p_set_top_of_book_price != nullptr and p_set_top_of_book_qty != nullptr and
                            p_set_top_of_book_premium != nullptr and p_set_top_of_book_last_barter_last_update_date_time != nullptr);

            PyObject* p_args = nullptr;
            void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
            std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);

            try {

                // std::lock_guard<std::mutex> lock(*lock_mutex);
                std::unique_lock<std::mutex> lock(*lock_mutex, std::try_to_lock_t{});
                if (!lock.owns_lock()) {
                    return;
                }
                p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book_obj.last_barter().px()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_price, p_args)));

                p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_of_book_obj.last_barter().qty()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_qty, p_args)));

                p_args = PyTuple_Pack(1, PyFloat_FromDouble(kr_top_of_book_obj.last_barter().premium()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_premium, p_args)));

                p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(
                        kr_top_of_book_obj.last_barter().last_update_date_time().c_str(),
                        static_cast<Py_ssize_t>(kr_top_of_book_obj.last_barter().last_update_date_time().size()),
                        nullptr));
                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_last_barter_last_update_date_time, p_args)));
                update_top_of_book_top_lev_fld(kr_top_of_book_obj, p_mobile_book_container_instance, p_mutex);
            } catch (std::exception& exception) {
                std::cerr << "Exception caught: " << exception.what() << std::endl;
            }
        }

        void update_top_of_book_top_lev_fld(const mobile_book::TopOfBook &kr_top_of_book_obj, PyObject* p_mobile_book_container_instance,
                                            PyObject* p_mutex) {

            PyObject* p_top_of_book_total_bartering_security_size = PyObject_GetAttrString(p_mobile_book_container_instance,
                                                                                         set_top_of_book_total_bartering_security_size_key.c_str());
            PyObject* p_set_top_of_book_mkt_barter_vol_participation_period_last_barter_qty_sum =
                    PyObject_GetAttrString(p_mobile_book_container_instance,
                                           set_top_of_book_market_barter_volume_participation_period_last_barter_qty_sum_key.c_str());
            PyObject* p_set_top_of_book_mkt_barter_vol_applicable_per_seconds =
                    PyObject_GetAttrString(p_mobile_book_container_instance,
                                           set_top_of_book_market_barter_volume_applicable_period_seconds_key.c_str());
            PyObject* p_set_top_of_book_last_update_date_time = PyObject_GetAttrString(p_mobile_book_container_instance,
                                                                                       set_top_of_book_last_update_date_time_key.c_str());

            assert(p_top_of_book_total_bartering_security_size != nullptr &&
                   p_set_top_of_book_mkt_barter_vol_participation_period_last_barter_qty_sum != nullptr &&
                   p_set_top_of_book_mkt_barter_vol_applicable_per_seconds != nullptr &&
                   p_set_top_of_book_last_update_date_time != nullptr);

            PyObject* p_args = nullptr;
            PyObject* p_result = nullptr;
            // void* p_void_mutex = PyLong_AsVoidPtr(p_mutex);
            // std::mutex* lock_mutex = static_cast<std::mutex*>(p_void_mutex);

            try {
//                std::lock_guard<std::mutex> lock(*lock_mutex);

                // std::unique_lock<std::mutex> lock(*lock_mutex, std::try_to_lock_t{});
                //
                // if (!lock.owns_lock()) {
                //     return;
                // }
                p_args = PyTuple_Pack(1, PyLong_FromLong(kr_top_of_book_obj.total_bartering_security_size()));
                assert(PyObject_IsTrue(PyObject_CallObject(p_top_of_book_total_bartering_security_size, p_args)));

                for (int i = 0; i < kr_top_of_book_obj.market_barter_volume_size(); ++i) {
                    p_result = set_market_barter_volume(p_mobile_book_container_instance,
                                                       kr_top_of_book_obj.market_barter_volume(i));
                    if (!PyObject_IsTrue(p_result)) {

                        p_args = PyTuple_Pack(2,
                                              PyUnicode_DecodeUTF8(kr_top_of_book_obj.market_barter_volume(i).id().c_str(),
                                                                   static_cast<Py_ssize_t>(kr_top_of_book_obj.market_barter_volume(
                                                                           i).id().size()), nullptr),
                                              PyLong_FromLong(kr_top_of_book_obj.market_barter_volume(
                                                      i).participation_period_last_barter_qty_sum()));
                        assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_mkt_barter_vol_participation_period_last_barter_qty_sum, p_args)));

                        p_args = PyTuple_Pack(2,
                                              PyUnicode_DecodeUTF8(kr_top_of_book_obj.market_barter_volume(i).id().c_str(),
                                                                   static_cast<Py_ssize_t>(kr_top_of_book_obj.market_barter_volume(
                                                                           i).id().size()), nullptr),
                                              PyLong_FromLong(kr_top_of_book_obj.market_barter_volume(
                                                      i).applicable_period_seconds()));
                        assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_mkt_barter_vol_applicable_per_seconds, p_args)));
                    }
                }

                p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_top_of_book_obj.last_update_date_time().c_str(),
                                                              static_cast<Py_ssize_t>(kr_top_of_book_obj.last_update_date_time().size()),
                                                              nullptr));

                assert(PyObject_IsTrue(PyObject_CallObject(p_set_top_of_book_last_update_date_time, p_args)));
            } catch (std::exception& exception) {
                std::cerr << "Exception caught: " << exception.what() << std::endl;
            }
        }

        PyObject* set_market_barter_volume(PyObject* p_mobile_book_container_instance, const mobile_book::MarketBarterVolume &kr_market_barter_volume_obj) {
            PyObject* p_set_func = nullptr;
            PyObject* p_args = nullptr;

            p_set_func = PyObject_GetAttrString(p_mobile_book_container_instance, set_top_of_book_market_barter_volume_key.c_str());
            assert(p_set_func != nullptr);

            p_args = PyTuple_Pack(3, PyUnicode_DecodeUTF8(kr_market_barter_volume_obj.id().c_str(),
                                                          static_cast<Py_ssize_t>(kr_market_barter_volume_obj.id().size()),
                                                          nullptr),
                                  PyLong_FromLong(kr_market_barter_volume_obj.participation_period_last_barter_qty_sum()),
                                  PyLong_FromLong(kr_market_barter_volume_obj.applicable_period_seconds()));
            return PyObject_CallObject(p_set_func, p_args);
        }

    };

}
