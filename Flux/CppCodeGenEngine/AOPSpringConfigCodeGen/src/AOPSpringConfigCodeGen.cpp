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

class AOPSpringConfigCodeGen: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
		
	public:

		AOPSpringConfigCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};




void AOPSpringConfigCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {
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
            printer.Print("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
            printer.Print("<beans xmlns=\"http://www.springframework.org/schema/beans\"\n");
            printer.Print("xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n");
            printer.Print("xmlns:tx=\"http://www.springframework.org/schema/tx\"\n");
            printer.Print("xmlns:aop=\"http://www.springframework.org/schema/aop\"\n");
            printer.Print("xsi:schemaLocation=\"\n");
            printer.Print("http://www.springframework.org/schema/beans http://www.springframework.org/schema/beans/spring-beans-2.5.xsd\n");
            printer.Print("http://www.springframework.org/schema/tx http://www.springframework.org/schema/tx/spring-tx-2.5.xsd\n");
            printer.Print("http://www.springframework.org/schema/aop http://www.springframework.org/schema/aop/spring-aop-2.5.xsd\">\n");
            printer.Print(variables,"<bean id=\"`capitalToLower`ThrowsAdvice\"\n");
            printer.Indent();
            printer.Print(variables,"class=\"`implclasspackage`.common.aop.`file_name`ThrowAdvice\" />\n");
            printer.Outdent();
            printer.Print("<aop:config>\n\n");
            printer.Indent();
            printer.Print(variables,"<aop:aspect id=\"afterThrowing`file_name`Exception\"\n");
            printer.Indent();
            printer.Print(variables,"ref=\"`capitalToLower`ThrowsAdvice\">\n");
            printer.Print(variables,"<aop:pointcut id=\"`capitalToLower`a\"\n");
            printer.Indent();
            printer.Print(variables,"expression=\"execution(* `implclasspackage`.services.impl.`file_name`TestImpl.*(..))\" />\n");
            printer.Outdent();
            printer.Print(variables,"<aop:after-throwing pointcut-ref=\"`capitalToLower`a\"\n");
			//get Projcet Name
            printer.Print("method=\"handle`project_name`Exception\" throwing=\"exception\" />\n",
						  "project_name", GetProjectName());
            printer.Outdent();
            printer.Print("</aop:aspect>\n");
            printer.Outdent();
            printer.Print("</aop:config>\n");
            printer.Print("<!-- Transaction Settings -->\n");
            printer.Print(variables,"<tx:advice id=\"tx`file_name`Advice\"\n");
            printer.Indent();
            printer.Print("transaction-manager=\"transactionManager\">\n");
            printer.Print("<!-- the transactional semantics... -->\n");
            printer.Print("<tx:attributes>\n");
            printer.Indent();
            printer.Print("<tx:method name=\"get*\" read-only=\"true\" />\n");
            printer.Print("<tx:method name=\"*\" propagation=\"REQUIRES_NEW\" />\n");
            printer.Outdent();
            printer.Print("</tx:attributes>\n");
            printer.Outdent();
            printer.Print("</tx:advice>\n");
            printer.Print("<aop:config>\n");
            printer.Indent();
            printer.Print(variables,"<aop:pointcut id=\"`capitalToLower`TxPoint\"\n");
            printer.Print(variables,"expression=\"execution(* `implclasspackage`.services.impl.`file_name`TestImpl.*(..))\" />\n");
            printer.Print(variables,"<aop:advisor advice-ref=\"tx`file_name`Advice\"\n");
            printer.Print(variables,"pointcut-ref=\"`capitalToLower`TxPoint\" />\n");
            printer.Outdent();
            printer.Print("</aop:config>\n");
            printer.Print(variables,"<tx:advice id=\"tx`file_name`DAOAdvice\"\n");
            printer.Indent();
            printer.Print("transaction-manager=\"transactionManager\">\n");
            printer.Print("<!-- the transactional semantics... -->\n");
            printer.Print("<tx:attributes>\n");
            printer.Indent();
            printer.Print("<tx:method name=\"get*\" read-only=\"true\" />\n");
            printer.Print("<!-- other methods use the default transaction settings (see below) -->\n");
            printer.Print("<tx:method name=\"*\" propagation=\"REQUIRED\" />\n");
            printer.Outdent();
            printer.Print("</tx:attributes>\n");
            printer.Outdent();
            printer.Print("</tx:advice>\n");
            printer.Print("<aop:config>\n");
            printer.Indent();
            printer.Print(variables,"<aop:pointcut id=\"`file_name`TxPoint\"\n");
            printer.Indent();
            printer.Print(variables,"expression=\"execution(* `implclasspackage`.dao.impl.`file_name`DaoImpl.*(..))\" />\n");
            printer.Outdent();
            printer.Print(variables,"<aop:advisor advice-ref=\"tx`file_name`DAOAdvice\"\n");
            printer.Indent();
            printer.Print(variables,"pointcut-ref=\"`file_name`TxPoint\" />\n");
            printer.Outdent();
            printer.Print("</aop:config>\n");
            printer.Print("<!-- End of Transaction settings -->\n");
            printer.Outdent();
           printer.Print("</beans>\n");
            /*_________________________________________________________________*/

}


bool AOPSpringConfigCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

            std::string cpp_filename ( file->name());
            size_t slashposition=cpp_filename.find_last_of ('/');
            size_t pos1 = cpp_filename.find_first_of ('.');
            std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
            size_t pf = sbstring.find_first_of ('.');
            std::string file_name=sbstring.substr(0,pf);
            
            scoped_ptr<io::ZeroCopyOutputStream> output(
            output_directory->Open(file_name+"AOP-SpringConfig.xml")
            );

            io::Printer printer(output.get(), '`');
            PrintMessages (printer, *file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	AOPSpringConfigCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
