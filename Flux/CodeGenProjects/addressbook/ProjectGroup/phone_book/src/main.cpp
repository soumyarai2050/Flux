#include "serialize_and_deserialize_using_proto2.h"
//#include "serialize_and_deserialize_using_proto3.h"

int main() {


    SerializeAndDeserializeProto2 serializeAndDeserializeProto2;
    auto order_journal = serializeAndDeserializeProto2.create_order_journal();
    std::string serialized_json = serializeAndDeserializeProto2.serialize_order_journal(order_journal);

    std::cout << "Serialized OrderJournal:\n" << serialized_json << std::endl;

    std::cout << "Deserialized OrderJournal:\n" << serializeAndDeserializeProto2.deserialize_order_journal(serialized_json).DebugString() << std::endl;
    google::protobuf::ShutdownProtobufLibrary();

    return 0;
}
