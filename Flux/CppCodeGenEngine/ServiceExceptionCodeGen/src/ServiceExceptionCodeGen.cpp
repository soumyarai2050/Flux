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

class ServiceExceptionCodeGen: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
	public:
		ServiceExceptionCodeGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void ServiceExceptionCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const 
{
            map <std::string,std::string>variables;
            std::string package=file.package();
            size_t pl=package.find_last_of('.');
            variables["implclasspackage"]=package.substr(0,pl);
            
            std::string cpp_filename (file.name());
            size_t slashposition=cpp_filename.find_last_of ('/');
            size_t pos1 = cpp_filename.find_first_of ('.');
            std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
            size_t pf = sbstring.find_first_of ('.');
            std::string file_name=sbstring.substr(0,pf);
            variables["file_name"]=file_name;
			//get Projcet Name
			variables["project_name"]=GetProjectName();
            printer.Print(variables,"package `implclasspackage`.exception;\n");

            printer.Print(variables,"public class `file_name`Exception extends `project_name`BaseException \n{\n");
            printer.Indent();
            printer.Print("private static final long serialVersionUID = 985587840751608280L;\n");
            printer.Print(variables,"public `file_name`Exception(String errorNo, String errorMsg) \n{\n");
            printer.Indent();
            printer.Print("super(errorNo, errorMsg);\n");
            printer.Outdent();
            printer.Print("}\n");
            printer.Print(variables,"public `file_name`Exception(String errorNo) \n{\n");
            printer.Indent();
            printer.Print("super(errorNo);\n");
            printer.Outdent();
            printer.Print("\n}\n");
            printer.Outdent();
            printer.Print("\n}\n");

}


bool ServiceExceptionCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	scoped_ptr<io::ZeroCopyOutputStream> output(
	output_directory->Open(GetPackageDirectoryName(file) + "/exception/" + GetFileNameFromFileDescriptor(file) + "Exception.java")
	);

	io::Printer printer(output.get(), '`');
	PrintMessages (printer, *file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	ServiceExceptionCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
