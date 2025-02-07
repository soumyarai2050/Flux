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
    std::string serialize_chore_journal(const phone_book::ChoreJournal& chore_journal);

    phone_book::ChoreJournal deserialize_chore_journal(const std::string& json_string);

    phone_book::ChoreJournal create_chore_journal();

};


#endif // HEADER_FILE_HPP

#endif //PAIR_STRAT_ENGINE_SERIALIZE_AND_DESERIALIZE_USING_PROTO2_H
