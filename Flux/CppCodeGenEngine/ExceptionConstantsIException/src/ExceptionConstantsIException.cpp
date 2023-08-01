/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class ExceptionConstantsIException: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
	public:
		ExceptionConstantsIException(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void ExceptionConstantsIException::PrintMessages(io::Printer &printer, const FileDescriptor & file) const 
{
         std::string package=file.package();
         size_t pos = package.find_last_of('.');
         std::string name=package.substr(0,pos);
         printer.Print("package `name`.constants;\n","name",name);
         printer.Print(" public interface IExceptionConstants \n{\n");
         printer.Indent();
         printer.Print("	String SERVER_INTERNAL_ERROR =\"SERVER_001\"; \n");
         printer.Print("	String UNKNOWN_DAO_ERROR = \"DAO_001\";\n");
         printer.Print("	String ERROR_SAVE_ADDRESS_BOOK = \"ADD_001\";\n");
         printer.Print("	String ERROR_UPDATE_ADDRESS_BOOK = \"ADD_002\";\n");
         printer.Print("	String ERROR_DELETE_ADDRESS_BOOK = \"ADD_003\";\n");
         printer.Outdent();	
         printer.Print("\n}\n");

     
}


bool ExceptionConstantsIException::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	scoped_ptr<io::ZeroCopyOutputStream> output(
	output_directory->Open(GetPackageDirectoryName(file) + "/constants/IExceptionConstants.java")
	);

	io::Printer printer(output.get(), '`');
	PrintMessages (printer, *file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	ExceptionConstantsIException generator;
	return PluginMain(argc, argv, &generator);
}
