#include "serialize_and_deserialize_using_proto2.h"
//#include "serialize_and_deserialize_using_proto3.h"

int main() {


    SerializeAndDeserializeProto2 serializeAndDeserializeProto2;
    auto chore_journal = serializeAndDeserializeProto2.create_chore_journal();
    std::string serialized_json = serializeAndDeserializeProto2.serialize_chore_journal(chore_journal);

    std::cout << "Serialized ChoreJournal:\n" << serialized_json << std::endl;

    std::cout << "Deserialized ChoreJournal:\n" << serializeAndDeserializeProto2.deserialize_chore_journal(serialized_json).DebugString() << std::endl;
    google::protobuf::ShutdownProtobufLibrary();

    return 0;
}
