#pragma once


#ifndef USE_LOGGING

#include <quill/Quill.h>

inline quill::Logger* GetCppAppLogger() {
    return nullptr;
}

#define LOG_ERROR_IMPL(X, ...) while(false) { }; // do { std::cout << ##__VA_ARGS__ << '\n'; }while(false);
#define LOG_INFO_IMPL(X, ...)  while(false) { };
#define LOG_DEBUG_IMPL(X, ...)  while(false) { };
#define LOG_WARNING_IMPL(X, ...)  while(false) { };
#define LOG_CRITICAL_IMPL(X, ...)  while(false) { };

#else
#include "../../../../../../../../../GitHub/TracticaTrading/DevUtils/logger.h"

inline quill::Logger* GetCppAppLogger() {
    return GetLogger();
}

#define LOG_INFO_IMPL(X, ...)  LOG_INFO(X, ##__VA_ARGS__);
#define LOG_ERROR_IMPL(X, ...)  LOG_ERROR(X, ##__VA_ARGS__);
#define LOG_DEBUG_IMPL(X, ...)  LOG_DEBUG(X, ##__VA_ARGS__);
#define LOG_WARNING_IMPL(X, ...)  LOG_WARNING(X, ##__VA_ARGS__);
#define LOG_CRITICAL_IMPL(X, ...)  LOG_CRITICAL(X, ##__VA_ARGS__);

#endif
