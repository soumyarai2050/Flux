#pragma once

#include <Python.h>
#include <iostream>
#include <string>
#include "utility_functions.h"

namespace FluxCppCore {

    struct AddOrGetContainerObj {

        static void add_container_obj_for_symbol(const std::string &kr_symbol) {
            Py_Initialize();

            {
                FluxCppCore::PythonGIL gil;

                if (cp_module == nullptr) {
                    cp_module = PyImport_ImportModule(mobile_book_handler::mobile_book_cache_module_name.c_str());
                    assert(cp_module != nullptr && "Failed to import module");
                }

                PyObject* p_add_container_obj_for_symbol_func_ = PyObject_GetAttrString(
                    cp_module, mobile_book_handler::add_container_obj_for_symbol_key.c_str());
                PyObject* p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(
                    kr_symbol.c_str(), static_cast<Py_ssize_t>(kr_symbol.size()), nullptr));
                PyObject_CallObject(p_add_container_obj_for_symbol_func_, p_args);
            }
        }

        static PyObject* get_mobile_book_container_instance(const std::string &kr_symbol) {
            PyObject* p_mobile_book_container_class = nullptr;
            PyObject* p_mobile_book_container_instance = nullptr;
            PyObject* p_args = nullptr;

            if (cp_module == nullptr) {
                cp_module = PyImport_ImportModule(mobile_book_handler::mobile_book_cache_module_name.c_str());
                assert(cp_module != nullptr);
            }

            p_mobile_book_container_class = PyObject_GetAttrString(cp_module, mobile_book_handler::get_mobile_book_container_key.c_str());
            assert(p_mobile_book_container_class != nullptr);

            p_args = PyTuple_Pack(1, PyUnicode_DecodeUTF8(kr_symbol.c_str(), static_cast<Py_ssize_t>(kr_symbol.size()), nullptr));
            p_mobile_book_container_instance = PyObject_CallObject(p_mobile_book_container_class, p_args);
            if (p_mobile_book_container_instance == Py_None) {
                return nullptr;
            } else {
                return p_mobile_book_container_instance;
            }
        }
    private:
        static PyObject* cp_module;
    };


}