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

class AOPServiceThrowAdviceCodeGen: public FluxCodeGenerator {
	protected:

		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;

	public:

		AOPServiceThrowAdviceCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

void AOPServiceThrowAdviceCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {

	std::string cpp_filename ( file.name());
	size_t slashposition=cpp_filename.find_last_of ('/');
	size_t pos1 = cpp_filename.find_first_of ('.');
	std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
	size_t pf = sbstring.find_first_of ('.');
	std::string file_name=sbstring.substr(0,pf);
	map<std::string,std::string> variables;
	variables["ClassName"]=UnderscoresToCapitalizedCamelCase(file.package());
	variables["file_name"]=file_name;
	variables["capitalToLower"]=UnderscoresToCamelCase(file_name);
	std::string package=file.package();
	size_t pl=package.find_last_of('.');
	//variables["package"]=package;
	variables["implclasspackage"]=package.substr(0,pl);
	//get Projcet Name
	variables["project_name"]=GetProjectName();
	  
	printer.Print(variables,"package `implclasspackage`.common.aop;\n");

	printer.Print(variables,"import `implclasspackage`.constants.IExceptionConstants;\n");
	printer.Print(variables,"import `implclasspackage`.exception.`file_name`Exception;\n");
	printer.Print(variables,"import `implclasspackage`.exception.DAOException;\n");

	printer.Print(variables,"import `implclasspackage`.exception.`project_name`BaseException;\n");
	printer.Print("\n");
	printer.Print(variables,"public class `file_name`ThrowAdvice extends Abstract`project_name`ThrowAdvice {\n");
	printer.Print("\n");
	printer.Print(variables,"public void handleaddOrUpdate`file_name`Exception(Object[] args, Object target,\n");
	printer.Print("Throwable exception) {\n");
	printer.Print(variables,"if (exception instanceof `project_name`BaseException) {\n");
	printer.Print(variables,"`project_name`BaseException baseExp = (`project_name`BaseException) exception;\n");
	printer.Print("if (exception instanceof DAOException) {\n");
	printer.Print(variables,"throw new `file_name`Exception(\n");
	printer.Print("IExceptionConstants.ERROR_SAVE_ADDRESS_BOOK);\n");
	printer.Print("} else {\n");
	printer.Print("throw baseExp;\n");
	printer.Print("}\n");
	printer.Print("} else {\n");
	printer.Print("\n");
	printer.Print(variables,"throw new `file_name`Exception(IExceptionConstants.ERROR_SAVE_ADDRESS_BOOK);\n");
	printer.Print("}\n");
	printer.Print("}\n");
        printer.Print("}\n");

}


bool AOPServiceThrowAdviceCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
         std::string output_filename = GetPackageDirectoryName(file) + "/common/aop/" + GetFileNameFromFileDescriptor(file) + "ThrowAdvice.java";
         scoped_ptr<io::ZeroCopyOutputStream> output(output_directory->Open(output_filename));
         io::Printer printer(output.get(), '`');
         PrintMessages(printer, *file);
         return true;
}


int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
	sleep(30);
	AOPServiceThrowAdviceCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
