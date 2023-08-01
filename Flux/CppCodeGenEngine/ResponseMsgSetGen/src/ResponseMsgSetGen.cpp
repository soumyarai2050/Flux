/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <boost/serialization/vector.hpp>
#include <boost/serialization/set.hpp>
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class ResponseMsgSetGen: public FluxCodeGenerator {
	protected:

		void PrintMessage(const Descriptor & message) const;
		void PrintComplexMessage(const Descriptor & message ) const;
		
		void PrintMessages  (const FileDescriptor & file) const;
		
	public:

		ResponseMsgSetGen(){}
                 mutable std::set<std::string> is; 
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};



void ResponseMsgSetGen::PrintComplexMessage(const Descriptor & message ) const 
{
	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		const FieldDescriptor &field ( *message.field(i) );
		if (field.type() == FieldDescriptor::TYPE_MESSAGE || field.type() == FieldDescriptor::TYPE_GROUP) 
		{
			isComplex = true;
		}
		if(isComplex)//Process only complex messages
		{
			const Descriptor & newMessage(*field.message_type());
			std::string strMsgNoExpand=newMessage.options().GetExtension(FluxMsgNoExpand);
			if(0!=strMsgNoExpand.length() && strMsgNoExpand != "!")
			{
				is.insert(UnqualifiedClassOrEnumOrFieldName(newMessage));
			}
			//Repeat for all complex types irrespective, because:
			//Even if this complex type expands inline, there may be other types defined in this type that do not expand inline
			PrintComplexMessage(newMessage);
		}//else not required, this is a simple type, jut ignore
	}
}


void ResponseMsgSetGen::PrintMessage(const Descriptor & message) const 
{
	std::string strFluxMsgRsp=message.options().GetExtension(FluxMsgRsp);
	if(0!=strFluxMsgRsp.length() && strFluxMsgRsp != "!")
	{
		//Extract Descriptor of Response message from file
		const Descriptor * ptrRespMessage = GetNestedMessageDescriptorFromFile(strFluxMsgRsp, *(message.file()));
		if(0 == ptrRespMessage)
			throw "Impossible Situation, FluxMsgRsp is set but Response message not found in the proto";
		//Recursively Parse through the body and add all sub-complex messages with FluxMsgNoExpand set  into the set
		is.insert(UnqualifiedClassOrEnumOrFieldName(*ptrRespMessage));
		PrintComplexMessage(*ptrRespMessage);
	}
}

void ResponseMsgSetGen::PrintMessages(const FileDescriptor & file) const 
{
	ifstream ifile("../temp/ResponseMsgSetStore.txt");
	if (ifile)
		ReadStdSetFromFile(is,"../temp/ResponseMsgSetStore.txt");
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		PrintMessage(*file.message_type(i));
	}
	WriteStdSetToFile(is,"../temp/ResponseMsgSetStore.txt");
}


bool ResponseMsgSetGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{	
	//Execute this only if proto is a service containor file
	//Get the FluxFileModelType file option, we execute further only if the model was a Service Model
	std::string strFileModelType = file->options().GetExtension(FluxFileModelType);
	if(strFileModelType == "SERVICE")
		PrintMessages  (*file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	ResponseMsgSetGen generator;
	return PluginMain(argc, argv, &generator);
}
