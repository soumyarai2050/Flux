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

class AOPAbstractProjectThrowAdvice: public FluxCodeGenerator 
{
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
	public:
		AOPAbstractProjectThrowAdvice(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};


void AOPAbstractProjectThrowAdvice::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {

	map<std::string,std::string> variables;
	std::string package=file.package();
	size_t pos = package.find_last_of('.');
	std::string name = ReplaceDotWithSlash(package.substr(0,pos));
	variables["implclasspackage"]=package.substr(0,pos);
	//get Projcet Name
	variables["project_name"] = GetProjectName();
	printer.Print(variables,"package `implclasspackage`.common.aop;\n");

	printer.Print(variables,"import static `implclasspackage`.constants.IExceptionConstants.SERVER_INTERNAL_ERROR;\n");

	printer.Print("import java.lang.reflect.Method;\n");

	printer.Print("import org.aspectj.lang.JoinPoint;\n");
	printer.Print("import org.hibernate.exception.ConstraintViolationException;\n");

	printer.Print(variables,"import `implclasspackage`.exception.`project_name`BaseException;\n\n");

	printer.Print(variables,"public abstract class Abstract`project_name`ThrowAdvice {\n");

	printer.Print("    protected String HANDLE_METHOD_PREFIX = \"handle\";\n");

	printer.Print("    protected String HANDLE_METHOD_SUFIX = \"Exception\";\n");

	printer.Print("    public static String CONSTRAINTS_VIOLATION = \"DAO_002\";\n");

	printer.Print("    private void checkForConstraintsViolation(Throwable exception)\n");
	printer.Print(variables,"	   throws `project_name`BaseException {\n");
	printer.Print("	exception.printStackTrace();\n");
	printer.Print("	Throwable subCause = null;\n");
	printer.Print("	ConstraintViolationException constVioException = null;\n");
	printer.Print("	subCause = exception.getCause();\n");
	printer.Print("\n");
	printer.Print("	int i = 0;\n");
	printer.Print("\n");
	printer.Print("	while (i < 3) {\n");
	printer.Print("	    i++;\n");
	printer.Print("	    if (subCause == null)\n");
	printer.Print("		break;\n");
	printer.Print("	    if (subCause instanceof ConstraintViolationException) {\n");
	printer.Print("		constVioException = (ConstraintViolationException) subCause;\n");
	printer.Print("		break;\n");
	printer.Print("	    }\n");
	printer.Print("	    subCause = subCause.getCause();\n");
	printer.Print("\n");
	printer.Print("	}\n");
	printer.Print("\n");
	printer.Print("	if (constVioException != null) {\n");
	printer.Print("	    String[] params = new String[1];\n");
	printer.Print("	    params[0] = constVioException.getConstraintName();\n");
	printer.Print(variables,"	    throw new `project_name`BaseException(CONSTRAINTS_VIOLATION, constVioException\n");
	printer.Print("		    .getMessage(), constVioException, params);\n");
	printer.Print("	}\n");
 	printer.Print("  }\n");
	printer.Print(variables,"    protected void handle`project_name`Exception(JoinPoint jp, Throwable exception)\n");
	printer.Print("	    throws Exception {\n");
	printer.Print("\n");
	printer.Print("	checkForConstraintsViolation(exception);\n");
	printer.Print("\n");
	printer.Print("	String methodName = jp.getSignature().getName();\n");
	printer.Print("\n");
	printer.Print("	String handleMethodName = HANDLE_METHOD_PREFIX + methodName\n");
	printer.Print("		+ HANDLE_METHOD_SUFIX;\n");
	printer.Print("\n");
	printer.Print("	Object[] methodArgs = jp.getArgs();\n");
	printer.Print("\n");
	printer.Print("	Object targetObj = jp.getTarget();\n");
	printer.Print("\n");
	printer.Print("	Class[] handlerMethodTypes = new Class[] { Object[].class,\n");
	printer.Print("		Object.class, Throwable.class };\n");
	printer.Print("	Object[] handlerMethodArgs = new Object[] { methodArgs, targetObj,\n");
	printer.Print("		exception };\n");
	printer.Print("\n");
	printer.Print("	try {\n");
	printer.Print("	    Method handlerMethod = this.getClass().getMethod(handleMethodName,\n");
	printer.Print("		    handlerMethodTypes);\n");
	printer.Print("	    handlerMethod.invoke(this, handlerMethodArgs);\n");
	printer.Print("\n");
	printer.Print("	} catch (Exception e) {\n");
	printer.Print("\n");
	printer.Print(variables,"	    if (e.getCause() instanceof `project_name`BaseException) {\n");
	printer.Print(variables,"		`project_name`BaseException baseExp = (`project_name`BaseException) e.getCause();\n");
	printer.Print("		throw baseExp;// throw it to GUI Layer\n");
	printer.Print("	    } else \n");
	printer.Print("	    {\n");
	printer.Print(variables,"		throw new `project_name`BaseException(\n");
	printer.Print("			SERVER_INTERNAL_ERROR, \"\");\n");
	printer.Print("\n");
	printer.Print("	    }\n");

	printer.Print("	}\n");

	printer.Print("    }\n");

	printer.Print("}\n");



}


bool AOPAbstractProjectThrowAdvice::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	std::string output_filename =GetPackageDirectoryName(file)+"/common/aop/"+"Abstract" + GetProjectName() +"ThrowAdvice.java";
	scoped_ptr<io::ZeroCopyOutputStream> output(output_directory->Open(output_filename));
	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	AOPAbstractProjectThrowAdvice generator;
	return PluginMain(argc, argv, &generator);
}
