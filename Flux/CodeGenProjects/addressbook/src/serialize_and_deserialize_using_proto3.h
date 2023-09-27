//
// Created by pc on 5/28/2023.
//

#ifndef PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
#define PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
#include "generated/strat_manager_service3.pb.h"
#include "google/protobuf/util/json_util.h"

class SerializeAndDeserializeProto3 {

public:

    std::string serialize_order_journal(const addressbook::OrderJournal& order_journal);

    addressbook::OrderJournal deserialize_order_journal(const std::string& json_string);

    addressbook::OrderJournal create_order_journal();
};
#endif //PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
