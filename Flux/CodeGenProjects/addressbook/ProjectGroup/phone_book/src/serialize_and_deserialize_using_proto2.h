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
#include "email_book_service.pb.h"
#include "plan_core.pb.h"

class SerializeAndDeserializeProto2 {

public:
    std::string serialize_chore_ledger(const phone_book::ChoreLedger& chore_ledger);

    phone_book::ChoreLedger deserialize_chore_ledger(const std::string& json_string);

    phone_book::ChoreLedger create_chore_ledger();

};


#endif // HEADER_FILE_HPP

#endif //PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO2_H
