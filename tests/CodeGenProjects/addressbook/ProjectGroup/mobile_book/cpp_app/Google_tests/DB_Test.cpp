//
// Created by pc on 6/8/2023.
//

#include <cstdlib>

#include "mobile_book_mongo_db_test.h"
#include "mobile_book_web_client_test.h"
#include "mobile_book_codec_test.h"
#include "mobile_book_web_socket_test.h"

int main(int argc, char** argv) {
    quill::start();
    // Set the environment variable to break on failure
    setenv("GTEST_BREAK_ON_FAILURE", "1", 1);

    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}