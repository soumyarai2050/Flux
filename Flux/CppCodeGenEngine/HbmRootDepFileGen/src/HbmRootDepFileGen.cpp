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

class HbmRootDepFileGen: public FluxCodeGenerator {
	protected:

		void PrintMessage(const Descriptor & message) const;
		void PrintComplexMessage(const Descriptor & message ) const;
		
		void PrintMessages  (const FileDescriptor & file) const;
		
	public:

		HbmRootDepFileGen(){}
                 mutable std::set<std::string> is; 
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};



void HbmRootDepFileGen::PrintComplexMessage(const Descriptor & message ) const 
{
	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		const FieldDescriptor &field ( *message.field(i) );
		if (field.type() == FieldDescriptor::TYPE_MESSAGE || field.type() == FieldDescriptor::TYPE_GROUP) 
		{
			isComplex = true;
		}
		if(isComplex)
		{
			const Descriptor & newMessage(*field.message_type());
			std::string strMsgNoExpand=newMessage.options().GetExtension(FluxMsgNoExpand);
			if(0!=strMsgNoExpand.length() && strMsgNoExpand != "!")
			{
				//A nested type (reapeted or not) is a HBMRoot iff FluxMsgNoExpand defined for this type
				is.insert(UnqualifiedClassOrEnumOrFieldName(newMessage));
			}
			//Repeat for all complex types irrespective, because:
			//Even if this complex type expands inline, there may be other types defined in this type that do not expand inline
			PrintComplexMessage(newMessage);
		}//else not required, this is a simple type, jut ignore
	}
}


void HbmRootDepFileGen::PrintMessage(const Descriptor & message) const 
{
	std::string strHbmRoot=message.options().GetExtension(FluxMsgOrmRoot);
	if(0!=strHbmRoot.length() && strHbmRoot != "!")
	{
		std::string strMsgNoExpand=message.options().GetExtension(FluxMsgNoExpand);
		if(0!=strMsgNoExpand.length() && strMsgNoExpand != "!")
		{
			is.insert(UnqualifiedClassOrEnumOrFieldName(message));
			PrintComplexMessage(message );
		}
		else
		{
			throw "Invalid Proto File - If a message has FluxMsgOrmRoot set, it must have FluxMsgNoExpand set as well";
		}
	}
}

void HbmRootDepFileGen::PrintMessages(const FileDescriptor & file) const {
   ifstream ifile("../temp/HbmRootStore.txt");
    if (ifile)
     ReadStdSetFromFile(is,"../temp/HbmRootStore.txt");
	for (int i = 0; i < file.message_type_count(); ++i) {
           
		PrintMessage(*file.message_type(i));
	}
        WriteStdSetToFile(is,"../temp/HbmRootStore.txt");
}


bool HbmRootDepFileGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

	
	PrintMessages(*file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	HbmRootDepFileGen generator;
	return PluginMain(argc, argv, &generator);
}
