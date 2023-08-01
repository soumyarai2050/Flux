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

class DAOThrowAdviceCodeGen: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;		
	public:
		DAOThrowAdviceCodeGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void DAOThrowAdviceCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const 
{
	map<std::string,std::string> variables;
	std::string package=file.package();
	size_t pos = package.find_last_of('.');
	std::string name = ReplaceDotWithSlash(package.substr(0,pos));
	variables["implclasspackage"]=package.substr(0,pos);
		
	printer.Print(variables,"		package `implclasspackage`.common.aop;\n");

	printer.Print(variables,"		import static `implclasspackage`.constants.IExceptionConstants.UNKNOWN_DAO_ERROR;\n");

	printer.Print("		import java.lang.reflect.Method;\n");

	printer.Print("		import org.aspectj.lang.JoinPoint;\n");

	printer.Print(variables,"		import `implclasspackage`.exception.DAOException;\n");

	printer.Print("\n");

	//get Projcet Name
	std::string strProjectName=GetProjectName();
	printer.Print("		public class DAOThrowAdvice extends Abstract`project_name`ThrowAdvice {\n",
				  "project_name", strProjectName);

	printer.Print("\n");
	printer.Print("			public void handle`project_name`Exception(JoinPoint jp, Throwable exception) throws Exception {\n", 
				  "project_name", strProjectName);
	printer.Print("				String methodName = jp.getSignature().getName();\n");

	printer.Print("				String handleMethodName = HANDLE_METHOD_PREFIX + methodName + HANDLE_METHOD_SUFIX;\n");

	printer.Print("				Object[] methodArgs = jp.getArgs();\n");

	printer.Print("				Object targetObj = jp.getTarget();\n");

	printer.Print("				Class[] handlerMethodTypes = new Class[] { Object[].class, Object.class, Throwable.class };\n");
	printer.Print("				Object[] handlerMethodArgs = new Object[] { methodArgs, targetObj, exception };\n");

	printer.Print("				try {\n");
	printer.Print("					Method handlerMethod = this.getClass().getMethod(handleMethodName, handlerMethodTypes);\n");
	printer.Print("					handlerMethod.invoke(this, handlerMethodArgs);\n");
	printer.Print("				} catch (Exception e) {\n");

	printer.Print("					throw new DAOException(UNKNOWN_DAO_ERROR, \"Unknown Error occured while Handling Exception\", exception, null);\n");
	printer.Print("				}\n");
	printer.Print("			}\n");
	printer.Print("		}\n");
}


bool DAOThrowAdviceCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	std::string output_filename =GetPackageDirectoryName(file) + "/common/aop/" + "DAOThrowAdvice.java";
	scoped_ptr<io::ZeroCopyOutputStream> output(output_directory->Open(output_filename));
	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}


int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
	sleep(30);
	DAOThrowAdviceCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
