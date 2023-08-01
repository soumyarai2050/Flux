//#include "serialize_and_deserialize_using_proto2.h"
//#include "serialize_and_deserialize_using_proto3.h"

#include "market_data_web_socket_server.h"
#include "market_data_web_socket_client.h"

int main() {

//    MarketDataWebSocketServer marketDataWebSocketServer;
//    marketDataWebSocketServer.run();

    std::string server_addr = "localhost";
    MarketDataWebSocketClient marketDataWebSocketClient(server_addr);
    marketDataWebSocketClient.run();

//    SerializeAndDeserializeProto2 serializeAndDeserializeProto2;
//    std::vector<market_data::TopOfBook> top_of_book_list = serializeAndDeserializeProto2.create_top_of_book();
//
//    std::vector<std::string> serialized_json_list = serializeAndDeserializeProto2.serialize_top_of_book(top_of_book_list);
//
//    for (auto& serialized_json : serialized_json_list) {
//        std::cout << serialized_json << std::endl;
//    }
//
//    for (auto& serialized_json: serialized_json_list) {
//        auto deserialized_obj = serializeAndDeserializeProto2.deserialize_top_of_book(serialized_json);
//        std::cout << deserialized_obj.DebugString() << std::endl;
//    }


    return 0;

}
