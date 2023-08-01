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

class BaseExceptionCodeGen: public FluxCodeGenerator {
	protected:

		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
	public:

		BaseExceptionCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

void BaseExceptionCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {

                        map <std::string,std::string>variables;
                        std::string package=file.package();
                        size_t pl=package.find_last_of('.');
                        variables["implclasspackage"]=package.substr(0,pl);
                        
                        printer.Print(variables,"package `implclasspackage`.exception;\n");
						//get Projcet Name
						std::string strProjectName=GetProjectName();
						printer.Print("public class `project_name`BaseException extends RuntimeException \n{\n",
									  "project_name", strProjectName);

                        
                        printer.Indent();
                        printer.Print("private static final long serialVersionUID = -7791736377308375758L;\n");
                        printer.Print("protected String errorNo = \"\";\n");
                        printer.Print("protected String[] errorParams;\n");
                        printer.Print("protected String errorDetail = \"\";\n");
                        printer.Print("public `project_name`BaseException() \n{\n",
									  "project_name", strProjectName);
                        // TODO(5) set default errorMsg and error No
                        // TODO(5) defining undefined error
                        printer.Print("}\n");
                        printer.Print("public `project_name`BaseException(String errorNo, String[] errorParams) \n{\n",
									  "project_name", strProjectName);
                        printer.Indent();
                        printer.Print("super();\n");
                        printer.Print("this.errorNo = errorNo;\n");
                        printer.Print("this.errorParams = errorParams;\n");
                        printer.Outdent();
                        printer.Print("}\n");
                        printer.Print("public `project_name`BaseException(String errorNo, String errorDetail)\n {\n",
									  "project_name", strProjectName);
                        printer.Indent();
                        printer.Print("this.errorNo = errorNo;\n");
                        printer.Print("this.errorDetail = errorDetail;\n");
                        printer.Outdent();
                        printer.Print("}\n");
                        printer.Print("public `project_name`BaseException(String errorNo, String detailErrorMsg,",
									  "project_name", strProjectName);
                        printer.Print("Throwable causedException, String[] params) \n{\n");
                        printer.Indent();
                        printer.Print("super(causedException);\n");
                        printer.Print("this.errorNo = errorNo;\n");
                        printer.Print("this.errorDetail = detailErrorMsg;\n");
                        printer.Print("this.errorParams = params;\n");
                        printer.Outdent();
                        printer.Print("}\n");
                        printer.Print("protected `project_name`BaseException(String errorNo) \n{\n",
									  "project_name", strProjectName);
                        printer.Indent();
                        printer.Print("this.errorNo = errorNo;\n");
                        printer.Outdent();
                        printer.Print("}\n");
                        printer.Print("public String getErrorDetail() \n{\n");
                        printer.Indent();
                        printer.Print("return errorDetail;\n");
                        printer.Outdent();
                        printer.Print("}\n");
                        printer.Print("public String getErrorCode() \n{\n");
                        printer.Indent();
                        printer.Print("return errorNo;\n");
                        printer.Outdent();
                        printer.Print("}\n");
                        printer.Print("public String[] getErrorParams() \n{\n");
                        printer.Indent();
                        printer.Print("return errorParams;\n");
                        printer.Outdent();
                        printer.Print("\n}\n");
                        printer.Outdent();
                        printer.Print("\n}\n");





}


bool BaseExceptionCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
            scoped_ptr<io::ZeroCopyOutputStream> output(
            	output_directory->Open(GetPackageDirectoryName(file)+"/exception/" + GetProjectName() + "BaseException.java")
            );

            io::Printer printer(output.get(), '`');
            PrintMessages (printer, *file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	BaseExceptionCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
