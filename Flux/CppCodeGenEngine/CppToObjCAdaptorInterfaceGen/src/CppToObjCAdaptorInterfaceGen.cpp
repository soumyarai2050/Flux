/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

#define COMP_NAME ""

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class CppToObjCAdaptorInterfaceGen: public FluxCodeGenerator
{
	protected:
		void PrintDependencies(io::Printer &printer, const FileDescriptor & file) const ;
		void PrintStaticDependencies(io::Printer &printer, const FileDescriptor & file) const;
		void PrintDynamicAdaptorDependencies(io::Printer &printer, const Descriptor & message) const;
		void PrintDynamicObjCClassDependencies(io::Printer &printer, const Descriptor & message) const;

		void PrintCppToObjCAdaptorInterface(io::Printer &printer, const Descriptor & message)const;
		void PrintMessages  (const FileDescriptor & file, io::Printer &printer) const;
		bool IsCodeGenRequired(const FileDescriptor& file)const;

		mutable std::set<std::string> responseMsgSet;
		mutable std::set<std::string> resolvedAdaptorDepFileNameSet;
		mutable std::set<std::string> resolvedObjCClasDepFileNameSet;

	public:
		CppToObjCAdaptorInterfaceGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void CppToObjCAdaptorInterfaceGen::PrintDependencies(io::Printer &printer, const FileDescriptor & file) const 
{
	//First Print Static Dependencies
	PrintStaticDependencies(printer, file);
	//Now Print Dynamic Dependencies
	//Sequence is: 
	//1. Cpp Dependency (1 File -1 File - One per file)
	//2. ObjC Class Dependency (1 MessageType - 1 MessageFile - check Unique)
	//3. Adaptor Dependency (1 MessageType - 1 Containor file - check unique)

	//1. Cpp Dependency
	printer.Print("//Cpp Dependency\n");
	printer.Print("#include \"`file_name`.pb.h\"\n","file_name",GetFileNameFromFileDescriptor(&file));
	//Add seperator after dependencies
	printer.Print("\n");

	//2. ObjC Class Dependency
	printer.Print("//ObjC Class Dependency\n");
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor &message = *file.message_type(i);
		if(responseMsgSet.end() != responseMsgSet.find(UnqualifiedClassOrEnumOrFieldName(message)))
		{
		   //This message is in the responseMsgSet - generate dependency
		   PrintDynamicObjCClassDependencies(printer, message);
		}
	}
	//Add seperator after dependencies
	printer.Print("\n");

	//3. Adaptor Dependency
	printer.Print("//Adaptor Dependency\n");
	//First Messages that are defined in this file have adaptors inside already so add current file as available dependency
	resolvedAdaptorDepFileNameSet.insert(GetFileNameFromFileDescriptor(&file));
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor &message = *file.message_type(i);
		if(responseMsgSet.end() != responseMsgSet.find(UnqualifiedClassOrEnumOrFieldName(message)))
		{
		   //This message is in the responseMsgSet - generate dependency
		   PrintDynamicAdaptorDependencies(printer, message);
		}
	}
	//Add seperator after dependencies
	printer.Print("\n");

}
void CppToObjCAdaptorInterfaceGen::PrintStaticDependencies(io::Printer &printer, const FileDescriptor & file) const 
{
	map<std::string, std::string> variables;
	variables["FileName"] = GetFileNameFromFileDescriptor(&file);
	variables["ModelName"] = file.name();
	variables["copy_right"] = getenv("COPY_RIGHT")?getenv("COPY_RIGHT"):"Copyright (c) 2012 __MyCompanyName__. All rights reserved.";

	printer.Print("//\n");
	printer.Print(variables,"// `FileName`_CppToObjCAdaptor.h\n");
	printer.Print(variables,"// Generated as Part of `ModelName`\n");
	printer.Print("// Created by Code Gen on Time Stamp same as File creation Time Stamp\n");
	printer.Print(variables,"// `copy_right`\n");
	printer.Print("//\n\n");
	printer.Print("#import \"FluxProtoObjCSupport.h\"\n");
}

void CppToObjCAdaptorInterfaceGen::PrintDynamicAdaptorDependencies(io::Printer &printer, const Descriptor & message) const 
{
	for (int i = 0; i < message.field_count(); ++i)
	{
		const FieldDescriptor &field ( *message.field(i) );
		if(FieldDescriptor::TYPE_MESSAGE == field.type() || FieldDescriptor::TYPE_GROUP == field.type()) 
		{
			const Descriptor &newmessage(*field.message_type());
			std::string depFileName = GetFileNameFromFileDescriptor(newmessage.file());
			if(resolvedAdaptorDepFileNameSet.end() == resolvedAdaptorDepFileNameSet.find(depFileName) )
			{
			   //This message is in the responseMsgSet - generate dependency
			   printer.Print("#import \"`FileName`.h\"\n","FileName",depFileName + "_CppToObjCAdaptor");
			   resolvedAdaptorDepFileNameSet.insert(depFileName);
			}
		}
	}
}

void CppToObjCAdaptorInterfaceGen::PrintDynamicObjCClassDependencies(io::Printer &printer, const Descriptor & message) const 
{
	//Check and add this message ObjC Class Dependency
	if(resolvedObjCClasDepFileNameSet.end() == resolvedObjCClasDepFileNameSet.find(UnqualifiedClassOrEnumOrFieldName(message)) )
	{
		printer.Print("#import \"`MessageName`.h\"\n","MessageName",UnqualifiedClassOrEnumOrFieldName(message));
		resolvedObjCClasDepFileNameSet.insert(UnqualifiedClassOrEnumOrFieldName(message));
	}
	
	for (int i = 0; i < message.field_count(); ++i)
	{
		const FieldDescriptor &field ( *message.field(i) );
		if(FieldDescriptor::TYPE_MESSAGE == field.type() || FieldDescriptor::TYPE_GROUP == field.type()) 
		{
			const Descriptor &newmessage(*field.message_type());
			if(resolvedObjCClasDepFileNameSet.end() == resolvedObjCClasDepFileNameSet.find(UnqualifiedClassOrEnumOrFieldName(newmessage)) )
			{
			   printer.Print("#import \"`MessageName`.h\"\n","MessageName",UnqualifiedClassOrEnumOrFieldName(newmessage));
			   resolvedObjCClasDepFileNameSet.insert(UnqualifiedClassOrEnumOrFieldName(newmessage));
			}
		}
	}
}


//No Recursion, just print this method signature and that's it!!
void CppToObjCAdaptorInterfaceGen::PrintCppToObjCAdaptorInterface(io::Printer &printer, const Descriptor & message)const
{
	map<std::string,std::string> variables;
	variables["RequestType"] = UnderscoresToCapitalizedCamelCase(message);
	variables["CamelCaseRequestVar"] = UnderscoresToCamelCase(message);
	variables["FullyQualifiedCppRequestType"] = QualifiedCppClassOrEnumName(message);
	variables["CppCamelCaseRequestVar"] = std::string("cpp_") + UnderscoresToCamelCase(message);
	
	printer.Print(variables,"bool CppToObjCAdaptor(`RequestType`* `CamelCaseRequestVar`, `FullyQualifiedCppRequestType`& `CppCamelCaseRequestVar`);\n");
}

void CppToObjCAdaptorInterfaceGen::PrintMessages(const FileDescriptor & file, io::Printer& printer) const 
{
	PrintDependencies(printer, file);

	//Now Print Body of local CPP Functions one per message that is a response
	for (int i = 0; i < file.message_type_count(); ++i)
	{
		const Descriptor &message = *file.message_type(i);
		if(responseMsgSet.end() != responseMsgSet.find(UnqualifiedClassOrEnumOrFieldName(message)))
		{
			//This message is in the responseMsgSet - generate code
			PrintCppToObjCAdaptorInterface(printer, message);
		}
	}
}

bool CppToObjCAdaptorInterfaceGen::IsCodeGenRequired(const FileDescriptor& file)const
{
	ifstream iResponseMsgSetStoreFile("../temp/ResponseMsgSetStore.txt");
	if (iResponseMsgSetStoreFile)		
		ReadStdSetFromFile(responseMsgSet,"../temp/ResponseMsgSetStore.txt");
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor & message(*file.message_type(i));
		if(responseMsgSet.end() != responseMsgSet.find(UnqualifiedClassOrEnumOrFieldName(message)))
		{
		   //Even finding one message that is in the responseMsgSet is good enough to indicate generation required
		   return true;
		}
	}
	return false;
}

bool CppToObjCAdaptorInterfaceGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{	
	//First Check if this file needs code Gen
	if(IsCodeGenRequired(*file))
	{
		std::string cppToObjCAdaptorName = "/"+ GetFileNameFromFileDescriptor(file) + "_CppToObjCAdaptor.h";
		scoped_ptr<io::ZeroCopyOutputStream> cppToObjCAdaptorOutput(output_directory->Open(cppToObjCAdaptorName));
		io::Printer printer(cppToObjCAdaptorOutput.get(), '`');

		PrintMessages  (*file,printer);
	}	
	return true;
}


int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	CppToObjCAdaptorInterfaceGen generator;
	return PluginMain(argc, argv, &generator);
}
