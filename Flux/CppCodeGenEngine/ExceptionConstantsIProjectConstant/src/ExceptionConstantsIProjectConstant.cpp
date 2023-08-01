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

class ExceptionConstantsIProjectConstant: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
	public:
		ExceptionConstantsIProjectConstant(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void ExceptionConstantsIProjectConstant::PrintMessages(io::Printer &printer, const FileDescriptor & file) const 
{
	map <std::string,std::string>variables;
	std::string package=file.package();
	size_t pl=package.find_last_of('.');
	variables["implclasspackage"]=package.substr(0,pl);
	variables["ProjectName"]=GetProjectName();
	printer.Indent();
	printer.Print(variables,"package `implclasspackage`.constants;\n\n");
	printer.Print(variables,"public interface I`ProjectName`Constants \n");
	printer.Print("{\n");
	printer.Print("		String ADD_SUCCESS =\"Record Added Succesfully\";\n");
	printer.Print("		String UPDATE_SUCCESS =\"Record Updated Succesfully\";\n");
	printer.Print("}\n");
	printer.Outdent();
}


bool ExceptionConstantsIProjectConstant::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	std::string strOutputFileName = GetPackageDirectoryName(file) + "/constants/I" + GetProjectName() + "Constants.java";
	scoped_ptr<io::ZeroCopyOutputStream> output(output_directory->Open(strOutputFileName));

	io::Printer printer(output.get(), '`');
	PrintMessages (printer, *file);
	return true;
}


int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	ExceptionConstantsIProjectConstant generator;
	return PluginMain(argc, argv, &generator);
}
