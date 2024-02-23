#ifndef MARKET_DATA_SERIALIZE_AND_DESERIALIZE_USING_PROTO2_H
#define MARKET_DATA_SERIALIZE_AND_DESERIALIZE_USING_PROTO2_H

#include "generated/mobile_book_service.pb.h"
#include <google/protobuf/util/json_util.h>

#include <iostream>

class SerializeAndDeserializeProto2 {
public:
    std::vector<std::string> serialize_top_of_book(std::vector<mobile_book::TopOfBook> top_of_book_list);

    mobile_book::TopOfBook deserialize_top_of_book(const std::string& json_string);

    std::vector<mobile_book::TopOfBook> create_top_of_book();


};  // class SerializeAndDeserializeProto2


#endif //MARKET_DATA_SERIALIZE_AND_DESERIALIZE_USING_PROTO2_H
