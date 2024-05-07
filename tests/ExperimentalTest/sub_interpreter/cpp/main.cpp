#include <iostream>
#include "python3.12/Python.h"

// Global variable for the interpreter state

extern "C" void initialize_new_interpreter() {
    Py_Initialize();

    {
        PyGILState_STATE gilStateState = PyGILState_Ensure();

        PyInterpreterConfig config;
        config.use_main_obmalloc = 0;
        config.allow_fork = 0;
        config.allow_exec = 0;
        config.allow_threads = 1;
        config.allow_daemon_threads = 0;
        config.check_multi_interp_extensions = 1;
        config.gil = PyInterpreterConfig_OWN_GIL;

        PyThreadState *interpreterState = NULL;
        PyStatus status = Py_NewInterpreterFromConfig(&interpreterState, &config);

        if (PyStatus_Exception(status)) {
            printf("Failed to create new interpreter.\n");
            std::cout << "Error message: " << status.err_msg << std::endl;
            PyGILState_Release(gilStateState);
            return;
        }
        Py_EndInterpreter(interpreterState);
    }
}



int main() {
    std::cout << "Hello, World!" << std::endl;

    return 0;
}
