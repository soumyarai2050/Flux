//
// Created by pc on 6/8/2023.
//
#include "market_data_max_id_handler.h"
#include "market_data_mongo_db_test.h"
#include "market_data_web_client_test.h"
#include "market_data_codec_test.h"

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}

