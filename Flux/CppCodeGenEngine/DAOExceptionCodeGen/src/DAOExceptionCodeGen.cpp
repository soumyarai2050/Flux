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

class DAOExceptionCodeGen: public FluxCodeGenerator {
	protected:

		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
	public:

		DAOExceptionCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

void DAOExceptionCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {
               map <std::string,std::string>variables;
               std::string package=file.package();
               size_t pl=package.find_last_of('.');
               variables["implclasspackage"]=package.substr(0,pl);
               printer.Print(variables,"package `implclasspackage`.exception;\n");
               printer.Print("public class DAOException extends `project_name`BaseException \n{\n",
							  "project_name", GetProjectName());
               printer.Indent();
               printer.Print("private static final long serialVersionUID = 6294022806217632399L;\n");
               printer.Print("public DAOException() \n{\n");
               printer.Indent();
               printer.Print("super();\n");
               printer.Outdent();
               printer.Print("}\n");
               printer.Print("public DAOException(String errorNo) {\n");
               printer.Indent();
               printer.Print("super(errorNo);\n");
               printer.Outdent();
               printer.Print("}\n");
               printer.Print("public DAOException(String errorNo, String detailErrorMsg,");
               printer.Print("Throwable causedException, String[] params) {\n");
               printer.Indent();
               printer.Print("super(errorNo, detailErrorMsg, causedException, params);\n");
               printer.Outdent();
               printer.Print("}\n");
               printer.Print("public DAOException(String errorNo, String[] params) {\n");
               printer.Indent();
               printer.Print("super(errorNo, params);\n");
               printer.Outdent();
               printer.Print("}\n");
               printer.Print("public DAOException(String errorNo, String detailErrorMsg) {\n");
               printer.Indent();
               printer.Print("super(errorNo, detailErrorMsg);\n");
               printer.Outdent();
               printer.Print("}\n");
               printer.Outdent();
               printer.Print("\n}\n");

}


bool DAOExceptionCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	scoped_ptr<io::ZeroCopyOutputStream> output(
		output_directory->Open(GetPackageDirectoryName(file) + "/exception/DAOException.java")
		);

	io::Printer printer(output.get(), '`');
	PrintMessages (printer, *file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	DAOExceptionCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
