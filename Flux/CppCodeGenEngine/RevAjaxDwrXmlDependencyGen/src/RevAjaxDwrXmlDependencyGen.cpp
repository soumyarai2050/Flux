/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-2
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <set>
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class RevAjaxDwrXmlDependencyGen: public FluxCodeGenerator 
{
	protected:
		void PopulateServiceNameDeligateMap(const FileDescriptor & file) const ;
		void PopulateMessageQualifiedNameSet(const FileDescriptor & file) const ;
		void PopulateEnumQualifiedNameSet(const FileDescriptor & file) const ;
		void PrintMessages  (const FileDescriptor & file) const;
	public:
		RevAjaxDwrXmlDependencyGen(){}
		
		mutable std::map<std::string,std::string> serviceNameDelegateMap;
		mutable std::set<std::string> messageQualifiedNameSet;
		mutable std::set<std::string> enumQualifiedNameSet;
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void RevAjaxDwrXmlDependencyGen::PopulateServiceNameDeligateMap(const FileDescriptor & file) const 
{
	std::string cpp_filename (file.name());
	size_t slashposition=cpp_filename.find_last_of ('/');
	size_t pos1 = cpp_filename.find_first_of ('.');
	std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
	size_t pfirst = sbstring.find_first_of ('.');

	std::string file_name=sbstring.substr(0,pfirst);
	std::string package =""+file.package().substr(0,file.package().find_first_of('.'))+".services.delegate."+file_name+"Delegate";
	serviceNameDelegateMap[file_name] = package;
}

void RevAjaxDwrXmlDependencyGen::PopulateMessageQualifiedNameSet(const FileDescriptor & file) const 
{
	for (int i = 0; i < file.message_type_count(); ++i) 
	{ 
		const Descriptor & newmessage(*file.message_type(i));
		std::string cpp_filename ( QualifiedJavaClassOrEnumName(newmessage)+"Dto" );
		size_t pos1 = cpp_filename.find_last_of ('.');
		cpp_filename.replace(pos1,1,".dto.");
		messageQualifiedNameSet.insert(cpp_filename); 
	}
}

void RevAjaxDwrXmlDependencyGen::PopulateEnumQualifiedNameSet(const FileDescriptor & file) const 
{
	for (int i = 0; i < file.enum_type_count(); ++i) 
	{ 
		enumQualifiedNameSet.insert(QualifiedJavaClassOrEnumName(*file.enum_type(i))); 
	}
}


void RevAjaxDwrXmlDependencyGen::PrintMessages(const FileDescriptor & file) const 
{

	//Populate ServiceName - Service Deligate Map
	std::string strFileModelType = file.options().GetExtension(FluxFileModelType);
	if(strFileModelType == "SERVICE")
	{
		ifstream ifile("../temp/ServiceNameDeligateMap.txt");
		if (ifile)
		{
			ReadStdMapFromFile(serviceNameDelegateMap,"../temp/ServiceNameDeligateMap.txt");
		}
		// Update messageQualifiedNameSet with messages from this proto file
		PopulateServiceNameDeligateMap(file);

		//Write updated messageQualifiedNameSet to MessageQualifiedNameSet.txt file
		WriteStdMapToFile(serviceNameDelegateMap,"../temp/ServiceNameDeligateMap.txt");
	}

	//Populate messages
	{
		//Read messageQualifiedNameSet from MessageQualifiedNameSet.txt file 
		ifstream ifile("../temp/MessageQualifiedDtoNameSet.txt");
		if (ifile)
		{
			ReadStdSetFromFile(messageQualifiedNameSet,"../temp/MessageQualifiedDtoNameSet.txt");
		}
		// Update messageQualifiedNameSet with messages from this proto file
		PopulateMessageQualifiedNameSet(file);

		//Write updated messageQualifiedNameSet to MessageQualifiedNameSet.txt file
		WriteStdSetToFile(messageQualifiedNameSet,"../temp/MessageQualifiedDtoNameSet.txt");
	}
	
	//Populate Enums
	{
		//Read enumQualifiedNameSet from EnumQualifiedNameSet.txt file 
		ifstream ifile("../temp/EnumQualifiedNameSet.txt");
		if (ifile)
		{
			ReadStdSetFromFile(enumQualifiedNameSet,"../temp/EnumQualifiedNameSet.txt");
		}
		//Update enumQualifiedNameSet with messages from this proto file
		PopulateEnumQualifiedNameSet(file);

		//Write updated enumQualifiedNameSet to EnumQualifiedNameSet.txt file
		WriteStdSetToFile(enumQualifiedNameSet,"../temp/EnumQualifiedNameSet.txt");
	}
}

bool RevAjaxDwrXmlDependencyGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	PrintMessages (*file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	RevAjaxDwrXmlDependencyGen generator;
	return PluginMain(argc, argv, &generator);
}
