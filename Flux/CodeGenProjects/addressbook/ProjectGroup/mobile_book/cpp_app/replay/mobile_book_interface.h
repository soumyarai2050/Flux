#pragma once

#include "mobile_book_consumer.h"
#include "config_parser.h"

#include <memory>

extern std::unique_ptr<Config> config;
extern std::shared_ptr<MobileBookConsumer> mobile_book_consumer;