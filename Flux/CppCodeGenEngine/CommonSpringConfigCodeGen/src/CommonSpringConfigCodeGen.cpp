/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-1
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class CommonSpringConfigCodeGen: public FluxCodeGenerator {
	protected:

		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
		
	public:

		CommonSpringConfigCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};


void CommonSpringConfigCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
{      
               map<std::string,std::string> variables;
               std::string package=file.package();
               size_t pl=package.find_last_of('.');
               //variables["package"]=package;
               variables["implclasspackage"]=package.substr(0,pl);
			   
			   variables["project_name"] = GetProjectName();
               printer.Print("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
               printer.Print("<beans xmlns=\"http://www.springframework.org/schema/beans\"\n");
               printer.Indent();
               printer.Print("xmlns:context=\"http://www.springframework.org/schema/context\"\n");
               printer.Print("xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n");
               printer.Print("xmlns:tx=\"http://www.springframework.org/schema/tx\"\n");
               printer.Print("xmlns:aop=\"http://www.springframework.org/schema/aop\"\n");
               printer.Print("xsi:schemaLocation=\"\n");
               printer.Outdent();
               printer.Print("http://www.springframework.org/schema/context\n");
               printer.Print("http://www.springframework.org/schema/context/spring-context-2.5.xsd\n");
               printer.Print("http://www.springframework.org/schema/beans http://www.springframework.org/schema/beans/spring-beans-2.5.xsd\n");
               printer.Print("http://www.springframework.org/schema/tx http://www.springframework.org/schema/tx/spring-tx-2.5.xsd\n");
               printer.Print("http://www.springframework.org/schema/aop http://www.springframework.org/schema/aop/spring-aop-2.5.xsd\">\n");
               printer.Print("<description>BeanFactory=(CommonSpringFactory)</description>\n");
               printer.Indent();
               printer.Print(variables,"<bean id=\"`project_name`DataSource\"\n");
               printer.Indent();
               printer.Print("class=\"org.apache.commons.dbcp.BasicDataSource\" destroy-method=\"close\">\n");
               printer.Print("<property name=\"driverClassName\" value=\"${jdbc.driverClassName}\"/>\n");
               printer.Print("<property name=\"url\" value=\"${jdbc.url}\" />\n");
               printer.Print("<property name=\"username\" value=\"${jdbc.username}\" />\n");
               printer.Print("<property name=\"password\" value=\"${jdbc.password}\" />\n");
               printer.Outdent();
               printer.Print("</bean> \n");
                printer.Print("<context:property-placeholder location=\"/WEB-INF/jdbc.properties\" />\n");
               printer.Print("<!-- Hibernate Settings -->\n");
               printer.Print(variables,"<bean id=\"`project_name`HibernateProperties\"\n");
               printer.Indent();
               printer.Print("class=\"org.springframework.beans.factory.config.PropertiesFactoryBean\">\n");
               printer.Indent();
               printer.Print("<property name=\"properties\">\n");
               printer.Indent();
               printer.Print("<props>\n");
               printer.Indent();
               printer.Print("<!-- <prop key=\"hibernate.hbm2ddl.auto\">update</prop>  -->\n");
               printer.Print("<prop key=\"hibernate.dialect\">\n");
               printer.Indent();
               printer.Print("org.hibernate.dialect.MySQLDialect\n");
               printer.Print("</prop>\n");
               printer.Print("<prop key=\"current_session_context_class\">thread</prop>\n");
               printer.Print("<prop key=\"hibernate.connection.release_mode\">\n");
               printer.Indent();
               printer.Print("after_statement\n");
               printer.Print("</prop>\n");
               printer.Print("<prop\n");
               printer.Indent();
               printer.Print("key=\"hibernate.transaction.flush_before_completion\">\n");
               printer.Print("true\n");
               printer.Print("</prop>\n");
               printer.Print("<prop key=\"hibernate.transaction.auto_close_session\">\n");
               printer.Indent();
               printer.Print("true\n");
               printer.Print("</prop>\n");
               printer.Print("<prop key=\"hibernate.hbm2ddl.auto\">update</prop>\n");
               printer.Print("</props>\n");
               printer.Print("</property>\n");
               printer.Print("</bean>\n");
               printer.Print("<!-- Hibernate SessionFactory -->\n");
               printer.Print(variables,"<bean id=\"`project_name`SessionFactory\"\n");
               printer.Indent();
               printer.Print("class=\"org.springframework.orm.hibernate3.LocalSessionFactoryBean\">\n");
               printer.Indent();
               printer.Print("<property name=\"dataSource\">\n");
               printer.Indent();
               printer.Print(variables,"<ref local=\"`project_name`DataSource\" />\n");
               printer.Print("</property>\n");
               printer.Print("<property name=\"hibernateProperties\">\n");
               printer.Indent();
               printer.Print(variables,"<ref bean=\"`project_name`HibernateProperties\" />\n");
               printer.Print("</property>\n");
               printer.Print("<!-- Must references all OR mapping files. -->\n");
               printer.Print("<property name=\"mappingDirectoryLocations\">\n");
               printer.Indent();
               printer.Print("<list>\n");
               printer.Indent();
               printer.Print("<value>/WEB-INF/hbm/</value>\n");
               printer.Print("</list>\n");
               printer.Print("</property>\n");
               printer.Outdent();
               printer.Print("</bean>\n");
               printer.Print("<bean id=\"transactionManager\"\n");
               printer.Indent();
               printer.Print("class=\"org.springframework.orm.hibernate3.HibernateTransactionManager\">\n");
               printer.Print("<property name=\"sessionFactory\">\n");
               printer.Indent();
               printer.Print(variables,"<ref bean=\"`project_name`SessionFactory\" />\n");
               printer.Print("</property>\n");
               printer.Outdent();
               printer.Print("</bean>\n");
               printer.Print(variables,"<bean id=\"DAOThrowsAdvice\" class=\"`implclasspackage`.common.aop.DAOThrowAdvice\" />\n");
               printer.Indent();
               printer.Print("<aop:config>\n");
               printer.Indent();
               printer.Print("<aop:aspect id=\"afterThrowingDAOException\"\n");
               printer.Indent();
               printer.Print("ref=\"DAOThrowsAdvice\">\n");
               printer.Print("<aop:pointcut id=\"DAOError\"\n");
               printer.Print(variables,"expression=\"execution(* `implclasspackage`.dao.*.*.*(..))\" />\n");
               printer.Print("<aop:after-throwing pointcut-ref=\"DAOError\"\n");
               printer.Print(variables,"method=\"handle`project_name`Exception\" throwing=\"exception\" />\n");
               printer.Outdent();
               printer.Print("</aop:aspect>\n");
               printer.Outdent();
               printer.Print("</aop:config>\n");
               printer.Outdent();
               printer.Print("</beans>\n");

}


bool CommonSpringConfigCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

	std::string output_filename ("Common-SpringConfig.xml");

	// Generate main file.
	scoped_ptr<io::ZeroCopyOutputStream> output(
		output_directory->Open(output_filename)
	);

	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	CommonSpringConfigCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
