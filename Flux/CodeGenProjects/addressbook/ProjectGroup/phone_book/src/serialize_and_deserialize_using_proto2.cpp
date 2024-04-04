//
// Created by pc on 5/30/2023.
//
#include "serialize_and_deserialize_using_proto2.h"

std::string SerializeAndDeserializeProto2::serialize_chore_journal(const phone_book::ChoreJournal& chore_journal) {
    std::string json_string;
    google::protobuf::util::MessageToJsonString(chore_journal, &json_string);

    return json_string;
}

phone_book::ChoreJournal SerializeAndDeserializeProto2::deserialize_chore_journal(const std::string& json_string) {
    phone_book::ChoreJournal chore_journal;

    google::protobuf::util::JsonStringToMessage(json_string, &chore_journal);

    return chore_journal;
}

phone_book::ChoreJournal SerializeAndDeserializeProto2::create_chore_journal() {
    phone_book::ChoreJournal choreJournal;
    choreJournal.set_id(1);

    choreJournal.mutable_chore()->set_chore_id("1");
    choreJournal.mutable_chore()->mutable_security()->set_sec_id("AAPL");
    choreJournal.mutable_chore()->mutable_security()->set_sec_type(SecurityType::SEC_TYPE_UNSPECIFIED);
    choreJournal.mutable_chore()->set_side(Side::BUY);
    choreJournal.mutable_chore()->set_qty(100);
    choreJournal.mutable_chore()->set_px(100.0);
    choreJournal.mutable_chore()->set_chore_notional(10.0);
    choreJournal.mutable_chore()->set_underlying_account("AAPL");
    choreJournal.set_chore_event_date_time(1565972800000);
    choreJournal.set_chore_event(phone_book::ChoreEventType::OE_NEW);

    return choreJournal;
}
