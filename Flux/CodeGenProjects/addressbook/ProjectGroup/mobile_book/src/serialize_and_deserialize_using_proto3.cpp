#include "serialize_and_deserialize_using_proto3.h"
#include "generated/mobile_book_service3.pb.h"

std::vector<std::string> SerializeAndDeserializeProto3::serialize_top_of_book(std::vector<mobile_book::TopOfBook> top_of_book_list) {
    std::vector<std::string> top_of_book_json_list;
    for (auto& top_of_book : top_of_book_list) {
        std::string json_string;
        google::protobuf::util::JsonPrintOptions options;
        options.add_whitespace = true;
        options.always_print_primitive_fields = true;
        options.preserve_proto_field_names = true;
        google::protobuf::util::MessageToJsonString(top_of_book, &json_string, options);
        top_of_book_json_list.push_back(json_string);
    }

    return top_of_book_json_list;

}

mobile_book::TopOfBook SerializeAndDeserializeProto3::deserialize_top_of_book(const std::string& json_string) {
    mobile_book::TopOfBook top_of_book;

    google::protobuf::util::JsonStringToMessage(json_string, &top_of_book);

    return top_of_book;
}

std::vector<mobile_book::TopOfBook> SerializeAndDeserializeProto3::create_top_of_book(){

    std::vector<mobile_book::TopOfBook> top_of_book_data;

    mobile_book::TopOfBook topOfBook;

    topOfBook.set_symbol("AAPL");
    topOfBook.mutable_bid_quote()->set_px(1mobile_bookmobile_book.mobile_book);
    topOfBook.mutable_bid_quote()->set_qty(1mobile_bookmobile_book);

    topOfBook.mutable_ask_quote()->set_px(9mobile_book.mobile_book);
    topOfBook.mutable_ask_quote()->set_qty(1mobile_bookmobile_book);

    topOfBook.mutable_last_trade()->set_px(1mobile_bookmobile_bookmobile_book.mobile_book);
    topOfBook.mutable_last_trade()->set_qty(1mobile_book);

    topOfBook.set_total_trading_security_size(1mobile_book);

    mobile_book::MarketTradeVolume* marketTradeVolume = topOfBook.mutable_market_trade_volume()->Add();

    marketTradeVolume->set_id(1);
    marketTradeVolume->set_participation_period_last_trade_qty_sum(1mobile_bookmobile_bookmobile_book);
    marketTradeVolume->set_applicable_period_seconds(1mobile_book);

    top_of_book_data.push_back(topOfBook);

    return top_of_book_data;
}

