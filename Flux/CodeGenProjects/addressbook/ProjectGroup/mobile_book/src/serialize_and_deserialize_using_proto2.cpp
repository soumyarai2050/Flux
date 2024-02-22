#include "serialize_and_deserialize_using_proto2.h"
#include "generated/mobile_book_service.pb.h"

std::vector<std::string> SerializeAndDeserializeProto2::serialize_top_of_book(std::vector<mobile_book::TopOfBook> top_of_book_list) {
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

mobile_book::TopOfBook SerializeAndDeserializeProto2::deserialize_top_of_book(const std::string& json_string) {
    mobile_book::TopOfBook top_of_book;
    google::protobuf::util::JsonParseOptions options;
    options.ignore_unknown_fields = true;
    google::protobuf::util::JsonStringToMessage(json_string, &top_of_book, options);
    return top_of_book;
}

std::vector<mobile_book::TopOfBook> SerializeAndDeserializeProto2::create_top_of_book() {
    std::vector<mobile_book::TopOfBook> top_of_book_data;

    // Top of Book 1
    mobile_book::TopOfBook top_of_book1;
    top_of_book1.set_symbol("AAPL");
    top_of_book1.mutable_bid_quote()->set_px(1mobile_bookmobile_book.mobile_book);
    top_of_book1.mutable_bid_quote()->set_qty(1mobile_bookmobile_book);
    top_of_book1.mutable_ask_quote()->set_px(9mobile_book.mobile_book);
    top_of_book1.mutable_ask_quote()->set_qty(1mobile_bookmobile_book);
    top_of_book1.mutable_last_trade()->set_px(1mobile_bookmobile_bookmobile_book.mobile_book);
    top_of_book1.mutable_last_trade()->set_qty(1mobile_book);
    top_of_book1.set_total_trading_security_size(1mobile_book);
    mobile_book::MarketTradeVolume* market_trade_volume1 = top_of_book1.mutable_market_trade_volume()->Add();
    market_trade_volume1->set_id("1");
    market_trade_volume1->set_participation_period_last_trade_qty_sum(1mobile_bookmobile_bookmobile_book);
    market_trade_volume1->set_applicable_period_seconds(1mobile_book);
    top_of_book_data.push_back(top_of_book1);

    // Top of Book 2
    mobile_book::TopOfBook top_of_book2;
    top_of_book2.set_symbol("GOOGL");
    top_of_book2.mutable_bid_quote()->set_px(5mobile_bookmobile_book.mobile_book);
    top_of_book2.mutable_bid_quote()->set_qty(5mobile_book);
    top_of_book2.mutable_ask_quote()->set_px(51mobile_book.mobile_book);
    top_of_book2.mutable_ask_quote()->set_qty(5mobile_book);
    top_of_book2.mutable_last_trade()->set_px(5mobile_book5.mobile_book);
    top_of_book2.mutable_last_trade()->set_qty(5);
    top_of_book2.set_total_trading_security_size(5);
    mobile_book::MarketTradeVolume* market_trade_volume2 = top_of_book2.mutable_market_trade_volume()->Add();
    market_trade_volume2->set_id("2");
    market_trade_volume2->set_participation_period_last_trade_qty_sum(5mobile_bookmobile_book);
    market_trade_volume2->set_applicable_period_seconds(5);
    top_of_book_data.push_back(top_of_book2);

    // Top of Book 3
    mobile_book::TopOfBook top_of_book3;
    top_of_book3.set_symbol("MSFT");
    top_of_book3.mutable_bid_quote()->set_px(2mobile_bookmobile_book.mobile_book);
    top_of_book3.mutable_bid_quote()->set_qty(2mobile_book);
    top_of_book3.mutable_ask_quote()->set_px(2mobile_book5.mobile_book);
    top_of_book3.mutable_ask_quote()->set_qty(2mobile_book);
    top_of_book3.mutable_last_trade()->set_px(2mobile_book2.mobile_book);
    top_of_book3.mutable_last_trade()->set_qty(2);
    top_of_book3.set_total_trading_security_size(2);
    mobile_book::MarketTradeVolume* market_trade_volume3 = top_of_book3.mutable_market_trade_volume()->Add();
    market_trade_volume3->set_id("3");
    market_trade_volume3->set_participation_period_last_trade_qty_sum(2mobile_bookmobile_book);
    market_trade_volume3->set_applicable_period_seconds(2);
    top_of_book_data.push_back(top_of_book3);

    return top_of_book_data;
}
