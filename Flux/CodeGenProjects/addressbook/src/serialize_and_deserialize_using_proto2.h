//
// Created by pc on 5/28/2023.
//

#ifndef PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO2_H
#define PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO2_H

#ifndef HEADER_FILE_HPP
#define HEADER_FILE_HPP

#include <iostream>
#include <string>
#include <google/protobuf/util/json_util.h>
#include <google/protobuf/message.h>
#include "strat_manager_service.pb.h"
#include "strat_core.pb.h"

class SerializeAndDeserializeProto2 {

public:
    std::string serialize_order_journal(const addressbook::OrderJournal& order_journal);

    addressbook::OrderJournal deserialize_order_journal(const std::string& json_string);

    addressbook::OrderJournal create_order_journal();

};


#endif // HEADER_FILE_HPP

#endif //PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO2_H
