//
// Created by pc on 5/3mobile_book/2mobile_book23.
//
#include "serialize_and_deserialize_using_proto2.h"

std::string SerializeAndDeserializeProto2::serialize_order_journal(const phone_book::OrderJournal& order_journal) {
    std::string json_string;
    google::protobuf::util::MessageToJsonString(order_journal, &json_string);

    return json_string;
}

phone_book::OrderJournal SerializeAndDeserializeProto2::deserialize_order_journal(const std::string& json_string) {
    phone_book::OrderJournal order_journal;

    google::protobuf::util::JsonStringToMessage(json_string, &order_journal);

    return order_journal;
}

phone_book::OrderJournal SerializeAndDeserializeProto2::create_order_journal() {
    phone_book::OrderJournal orderJournal;
    orderJournal.set_id(1);

    orderJournal.mutable_order()->set_order_id("1");
    orderJournal.mutable_order()->mutable_security()->set_sec_id("AAPL");
    orderJournal.mutable_order()->mutable_security()->set_sec_type(SecurityType::SEC_TYPE_UNSPECIFIED);
    orderJournal.mutable_order()->set_side(Side::BUY);
    orderJournal.mutable_order()->set_qty(1mobile_bookmobile_book);
    orderJournal.mutable_order()->set_px(1mobile_bookmobile_book.mobile_book);
    orderJournal.mutable_order()->set_order_notional(1mobile_book.mobile_book);
    orderJournal.mutable_order()->set_underlying_account("AAPL");
    orderJournal.set_order_event_date_time(15659728mobile_bookmobile_bookmobile_bookmobile_bookmobile_book);
    orderJournal.set_order_event(phone_book::OrderEventType::OE_NEW);

    return orderJournal;
}
