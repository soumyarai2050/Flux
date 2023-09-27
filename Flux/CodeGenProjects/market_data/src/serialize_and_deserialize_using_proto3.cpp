#include "serialize_and_deserialize_using_proto3.h"
#include "generated/market_data_service3.pb.h"

std::vector<std::string> SerializeAndDeserializeProto3::serialize_top_of_book(std::vector<market_data::TopOfBook> top_of_book_list) {
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

market_data::TopOfBook SerializeAndDeserializeProto3::deserialize_top_of_book(const std::string& json_string) {
    market_data::TopOfBook top_of_book;

    google::protobuf::util::JsonStringToMessage(json_string, &top_of_book);

    return top_of_book;
}

std::vector<market_data::TopOfBook> SerializeAndDeserializeProto3::create_top_of_book(){

    std::vector<market_data::TopOfBook> top_of_book_data;

    market_data::TopOfBook topOfBook;

    topOfBook.set_symbol("AAPL");
    topOfBook.mutable_bid_quote()->set_px(100.0);
    topOfBook.mutable_bid_quote()->set_qty(100);

    topOfBook.mutable_ask_quote()->set_px(90.0);
    topOfBook.mutable_ask_quote()->set_qty(100);

    topOfBook.mutable_last_trade()->set_px(1000.0);
    topOfBook.mutable_last_trade()->set_qty(10);

    topOfBook.set_total_trading_security_size(10);

    market_data::MarketTradeVolume* marketTradeVolume = topOfBook.mutable_market_trade_volume()->Add();

    marketTradeVolume->set_id(1);
    marketTradeVolume->set_participation_period_last_trade_qty_sum(1000);
    marketTradeVolume->set_applicable_period_seconds(10);

    top_of_book_data.push_back(topOfBook);

    return top_of_book_data;
}

