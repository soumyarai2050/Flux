/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <boost/serialization/set.hpp>
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class NoExpandMsgDb: public FluxCodeGenerator {
	protected:
		void PrintMessage(const Descriptor & message) const;
		void PrintMessages  (const FileDescriptor & file) const;
		
	public:
		NoExpandMsgDb(){}
		mutable std::set<std::string> is; 
		bool Generate(const FileDescriptor* file, const string& parameter, OutputDirectory* output_directory, string* error) const;
};

void NoExpandMsgDb::PrintMessage(const Descriptor & message) const 
{
	for (int i = 0; i < message.field_count(); ++i)
	{
		const FieldDescriptor &field ( *message.field(i) );
		if(FieldDescriptor::TYPE_MESSAGE == field.type() || FieldDescriptor::TYPE_GROUP == field.type())
		{
			const Descriptor &newmessage(*field.message_type());
			string strMsgNoExpand=newmessage.options().GetExtension(FluxMsgNoExpand);
			if(0!=strMsgNoExpand.length() && strMsgNoExpand.length()!='!')
			{
				//The insert may fail for duplicates, however we dont care to check (as we want to know "who all" not "how many times of who all")
				is.insert(UnqualifiedClassOrEnumOrFieldName(newmessage));
			}
			PrintMessage(newmessage );
		}//else not required, simple type have no role in expansion
	}
}

void NoExpandMsgDb::PrintMessages(const FileDescriptor & file) const 
{
	ifstream ifile("../temp/NoExpandMsgDb.txt");
    if (ifile)
		ReadStdSetFromFile(is,"../temp/NoExpandMsgDb.txt");
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor & message(*file.message_type(i));
		is.insert(UnqualifiedClassOrEnumOrFieldName(message));
		PrintMessage(message);
	}
	WriteStdSetToFile(is,"../temp/NoExpandMsgDb.txt");
}


bool NoExpandMsgDb::Generate(const FileDescriptor* file,
				const string& parameter,
				OutputDirectory* output_directory,
				string* error) const 
{
	//Get the FluxFileModelType file option, we execute further only if the model was a Service Model
	std::string strFileModelType = file->options().GetExtension(FluxFileModelType);
	if(strFileModelType == "SERVICE")
		PrintMessages(*file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	NoExpandMsgDb generator;
	return PluginMain(argc, argv, &generator);
}
