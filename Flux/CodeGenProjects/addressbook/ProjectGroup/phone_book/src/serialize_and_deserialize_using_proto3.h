//
// Created by pc on 5/28/2023.
//

#ifndef PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
#define PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
#include "generated/email_book_service3.pb.h"
#include "google/protobuf/util/json_util.h"

class SerializeAndDeserializeProto3 {

public:

    std::string serialize_chore_ledger(const phone_book::ChoreLedger& chore_ledger);

    phone_book::ChoreLedger deserialize_chore_ledger(const std::string& json_string);

    phone_book::ChoreLedger create_chore_ledger();
};
#endif //PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO3_H
