//
// Created by pc on 5/30/2023.
//

#include "serialize_and_deserialize_using_proto3.h"

std::string SerializeAndDeserializeProto3::serialize_order_journal(const addressbook::OrderJournal& order_journal) {
    std::string json_string;
    google::protobuf::util::MessageToJsonString(order_journal, &json_string);

    return json_string;
}

addressbook::OrderJournal SerializeAndDeserializeProto3::deserialize_order_journal(const std::string& json_string) {
    addressbook::OrderJournal order_journal;

    google::protobuf::util::JsonStringToMessage(json_string, &order_journal);

    return order_journal;
}

addressbook::OrderJournal SerializeAndDeserializeProto3::create_order_journal() {
    addressbook::OrderJournal orderJournal;
    orderJournal.set_id(1);
    orderJournal.mutable_order()->set_order_id("1");
    orderJournal.mutable_order()->mutable_security()->set_sec_id("AAPL");
    orderJournal.mutable_order()->mutable_security()->set_sec_type(addressbook::SecurityType::SEC_TYPE_UNSPECIFIED);
    orderJournal.mutable_order()->set_side(addressbook::Side::BUY);
    orderJournal.mutable_order()->set_qty(100);
    orderJournal.mutable_order()->set_px(100.0);
    orderJournal.mutable_order()->set_order_notional(10.0);
    orderJournal.mutable_order()->set_underlying_account("AAPL");
    orderJournal.set_order_event_date_time(1565972800000);
    orderJournal.set_order_event(addressbook::OrderEventType::OE_NEW);

    return orderJournal;
}