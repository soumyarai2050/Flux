//
// Created by pc on 5/28/2023.
//

#ifndef PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
#define PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
#include "generated/email_book_service3.pb.h"
#include "google/protobuf/util/json_util.h"

class SerializeAndDeserializeProto3 {

public:

    std::string serialize_chore_journal(const phone_book::ChoreJournal& chore_journal);

    phone_book::ChoreJournal deserialize_chore_journal(const std::string& json_string);

    phone_book::ChoreJournal create_chore_journal();
};
#endif //PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
