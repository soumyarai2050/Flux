//
// Created by pc on 5/28/2mobile_book23.
//

#ifndef PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
#define PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
#include "generated/strat_manager_service3.pb.h"
#include "google/protobuf/util/json_util.h"

class SerializeAndDeserializeProto3 {

public:

    std::string serialize_order_journal(const phone_book::OrderJournal& order_journal);

    phone_book::OrderJournal deserialize_order_journal(const std::string& json_string);

    phone_book::OrderJournal create_order_journal();
};
#endif //PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
