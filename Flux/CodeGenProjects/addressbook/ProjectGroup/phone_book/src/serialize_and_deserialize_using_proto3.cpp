//
// Created by pc on 5/30/2023.
//

#include "serialize_and_deserialize_using_proto3.h"

std::string SerializeAndDeserializeProto3::serialize_chore_ledger(const phone_book::ChoreLedger& chore_ledger) {
    std::string json_string;
    google::protobuf::util::MessageToJsonString(chore_ledger, &json_string);

    return json_string;
}

phone_book::ChoreLedger SerializeAndDeserializeProto3::deserialize_chore_ledger(const std::string& json_string) {
    phone_book::ChoreLedger chore_ledger;

    google::protobuf::util::JsonStringToMessage(json_string, &chore_ledger);

    return chore_ledger;
}

phone_book::ChoreLedger SerializeAndDeserializeProto3::create_chore_ledger() {
    phone_book::ChoreLedger choreLedger;
    choreLedger.set_id(1);
    choreLedger.mutable_chore()->set_chore_id("1");
    choreLedger.mutable_chore()->mutable_security()->set_sec_id("AAPL");
    choreLedger.mutable_chore()->mutable_security()->set_sec_type(phone_book::SecurityType::SEC_TYPE_UNSPECIFIED);
    choreLedger.mutable_chore()->set_side(phone_book::Side::BUY);
    choreLedger.mutable_chore()->set_qty(100);
    choreLedger.mutable_chore()->set_px(100.0);
    choreLedger.mutable_chore()->set_chore_notional(10.0);
    choreLedger.mutable_chore()->set_underlying_account("AAPL");
    choreLedger.set_chore_event_date_time(1565972800000);
    choreLedger.set_chore_event(phone_book::ChoreEventType::OE_NEW);

    return choreLedger;
}