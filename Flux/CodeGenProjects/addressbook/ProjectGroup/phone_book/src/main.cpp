#include "serialize_and_deserialize_using_proto2.h"
//#include "serialize_and_deserialize_using_proto3.h"

int main() {


    SerializeAndDeserializeProto2 serializeAndDeserializeProto2;
    auto chore_ledger = serializeAndDeserializeProto2.create_chore_ledger();
    std::string serialized_json = serializeAndDeserializeProto2.serialize_chore_ledger(chore_ledger);

    std::cout << "Serialized ChoreLedger:\n" << serialized_json << std::endl;

    std::cout << "Deserialized ChoreLedger:\n" << serializeAndDeserializeProto2.deserialize_chore_ledger(serialized_json).DebugString() << std::endl;
    google::protobuf::ShutdownProtobufLibrary();

    return 0;
}
