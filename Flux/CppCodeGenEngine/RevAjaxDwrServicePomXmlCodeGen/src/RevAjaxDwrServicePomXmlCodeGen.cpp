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

class RevAjaxDwrServicePomXmlCodeGen: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
		
	public:

		RevAjaxDwrServicePomXmlCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};


void RevAjaxDwrServicePomXmlCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const 
{
	map<std::string,std::string> variables;
	variables["project_name"]= GetProjectName();

	printer.Print("<project xmlns=\"http://maven.apache.org/POM/4.0.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n");
	printer.Print("xsi:schemaLocation=\"http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd\">\n");
	printer.Print("<modelVersion>4.0.0</modelVersion>\n");
	printer.Print("<groupId>project_service</groupId>\n");
	printer.Print("<artifactId>project_service</artifactId>\n");
	printer.Print("<packaging>jar</packaging>\n");
	printer.Print("<version>0.0.1-SNAPSHOT</version>\n");
	printer.Print("<!-- Shared version number properties -->\n");
	printer.Indent();
	printer.Print("<properties>\n");
	printer.Indent();
	printer.Print("<org.springframework.version>3.0.6.RELEASE</org.springframework.version>\n");
	printer.Outdent();
	printer.Print("</properties>\n");
	printer.Print("<dependencies>\n");
	printer.Indent();
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print(variables, "<groupId>`project_name`-daomodel</groupId>\n");
	printer.Print(variables, "<artifactId>`project_name`-daomodel</artifactId>\n");
	printer.Print("<version>0.0.1-SNAPSHOT</version>\n");
	printer.Print("<scope>compile</scope>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>aspectj</groupId>\n");
	printer.Print("<artifactId>aspectjrt</artifactId>\n");
	printer.Print("<version>1.2</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<!-- Core utilities used by other modules. Define this if you use Spring \n");
	printer.Print("Utility APIs (org.springframework.core.*/org.springframework.util.*) -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-core</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");

	printer.Print("<!-- Expression Language (depends on spring-core) Define this if you use \n");
	printer.Print("Spring Expression APIs (org.springframework.expression.*) -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-expression</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");

	printer.Print("<!-- Bean Factory and JavaBeans utilities (depends on spring-core) Define \n");
	printer.Print("this if you use Spring Bean APIs (org.springframework.beans.*) -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-beans</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");

	printer.Print("<!-- Aspect Oriented Programming (AOP) Framework (depends on spring-core, \n");
	printer.Print("spring-beans) Define this if you use Spring AOP APIs (org.springframework.aop.*) -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-aop</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");

	printer.Print("<!-- Application Context (depends on spring-core, spring-expression, spring-aop, \n");
	printer.Print("spring-beans) This is the central artifact for Spring's Dependency Injection \n");
	printer.Print("Container and is generally always defined -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-context</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");

	printer.Print("<!-- Various Application Context utilities, including EhCache, JavaMail, \n");
	printer.Print("Quartz, and Freemarker integration Define this if you need any of these integrations -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-context-support</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");

	printer.Print("<!-- Transaction Management Abstraction (depends on spring-core, spring-beans, \n");
	printer.Print("spring-aop, spring-context) Define this if you use Spring Transactions or \n");
	printer.Print("DAO Exception Hierarchy (org.springframework.transaction.*/org.springframework.dao.*) -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-tx</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");

	printer.Print("<!-- JDBC Data Access Library (depends on spring-core, spring-beans, spring-context, \n");
	printer.Print("spring-tx) Define this if you use Spring's JdbcTemplate API (org.springframework.jdbc.*) -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-jdbc</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");

	printer.Print("<!-- Object-to-Relation-Mapping (ORM) integration with Hibernate, JPA, \n");
	printer.Print("and iBatis. (depends on spring-core, spring-beans, spring-context, spring-tx) \n");
	printer.Print("Define this if you need ORM (org.springframework.orm.*) -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-orm</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<!-- Object-to-XML Mapping (OXM) abstraction and integration with JAXB, \n");
	printer.Print("JiBX, Castor, XStream, and XML Beans. (depends on spring-core, spring-beans, \n");
	printer.Print("spring-context) Define this if you need OXM (org.springframework.oxm.*) -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-oxm</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<!-- Web application development utilities applicable to both Servlet and \n");
	printer.Print("Portlet Environments (depends on spring-core, spring-beans, spring-context) \n");
	printer.Print("Define this if you use Spring MVC, or wish to use Struts, JSF, or another \n");
	printer.Print("web framework with Spring (org.springframework.web.*) -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-web</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<!-- Spring MVC for Servlet Environments (depends on spring-core, spring-beans, \n");
	printer.Print("spring-context, spring-web) Define this if you use Spring MVC with a Servlet \n");
	printer.Print("Container such as Apache Tomcat (org.springframework.web.servlet.*) -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-webmvc</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<!-- Support for testing Spring applications with tools such as JUnit and \n");
	printer.Print("TestNG This artifact is generally always defined with a 'test' scope for \n");
	printer.Print("the integration testing framework and unit testing stubs -->\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.springframework</groupId>\n");
	printer.Print("<artifactId>spring-test</artifactId>\n");
	printer.Print("<version>${org.springframework.version}</version>\n");
	printer.Print("<scope>test</scope>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.slf4j</groupId>\n");
	printer.Print("<artifactId>slf4j-log4j12</artifactId>\n");
	printer.Print("<version>1.6.3</version>\n");
	printer.Print("<type>jar</type>\n");
	printer.Print("<scope>compile</scope>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.slf4j</groupId>\n");
	printer.Print("<artifactId>slf4j-api</artifactId>\n");
	printer.Print("<version>1.6.3</version>\n");
	printer.Print("<type>jar</type>\n");
	printer.Print("<scope>compile</scope>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>log4j</groupId>\n");
	printer.Print("<artifactId>log4j</artifactId>\n");
	printer.Print("<version>1.2.16</version>\n");
	printer.Print("<type>pom</type>\n");
	printer.Print("<scope>compile</scope>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>com.google.code.gson</groupId>\n");
	printer.Print("<artifactId>gson</artifactId>\n");
	printer.Print("<version>1.7.1</version>\n");
	printer.Print("<scope>compile</scope>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.hibernate.javax.persistence</groupId>\n");
	printer.Print("<artifactId>hibernate-jpa-2.0-api</artifactId>\n");
	printer.Print("<version>1.0.1.Final</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.hibernate</groupId>\n");
	printer.Print("<artifactId>hibernate-entitymanager</artifactId>\n");
	printer.Print("<version>3.6.7.Final</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.restlet.jee</groupId>\n");
	printer.Print("<artifactId>org.restlet</artifactId>\n");
	printer.Print("<version>2.0.10</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.restlet.jee</groupId>\n");
	printer.Print("<artifactId>org.restlet.ext.servlet</artifactId>\n");
	printer.Print("<version>2.0.10</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>javax.ws.rs</groupId>\n");
	printer.Print("<artifactId>jsr311-api</artifactId>\n");
	printer.Print("<version>1.0</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>javax</groupId>\n");
	printer.Print("<artifactId>javaee-web-api</artifactId>\n");
	printer.Print("<version>6.0</version>\n");
	printer.Print("<scope>provided</scope>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");

	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>net.sf.nomin</groupId>\n");
	printer.Print("<artifactId>nomin</artifactId>\n");
	printer.Print("<version>1.1.1</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>uk.co.jemos.podam</groupId>\n");
	printer.Print("<artifactId>podam</artifactId>\n");
	printer.Print("<version>3.0.1.RELEASE</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>org.codehaus.groovy</groupId>\n");
	printer.Print("<artifactId>groovy</artifactId>\n");
	printer.Print("<version>1.8.4</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>com.google.guava</groupId>\n");
	printer.Print("<artifactId>guava</artifactId>\n");
	printer.Print("<version>10.0.1</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>commons-lang</groupId>\n");
	printer.Print("<artifactId>commons-lang</artifactId>\n");
	printer.Print("<version>2.6</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Print("<dependency>\n");
	printer.Indent();
	printer.Print("<groupId>commons-beanutils</groupId>\n");
	printer.Print("<artifactId>commons-beanutils</artifactId>\n");
	printer.Print("<version>1.8.3</version>\n");
	printer.Outdent();
	printer.Print("</dependency>\n");
	printer.Outdent();
	printer.Print("</dependencies>\n");
	printer.Print("<repositories>\n");
	printer.Indent();
	printer.Print("<repository>\n");
	printer.Indent();
	printer.Print("<id>maven-restlet</id>\n");
	printer.Print("<name>Public online Restlet repository</name>\n");
	printer.Print("<url>http://maven.restlet.org</url>\n");
	printer.Outdent();
	printer.Print("</repository>\n");
	printer.Print("<repository>\n");
	printer.Indent();
	printer.Print("<id>maven2-repository.dev.java.net</id>\n");
	printer.Print("<name>Java.net Repository for Maven</name>\n");
	printer.Print("<url>http://download.java.net/maven/2/</url>\n");
	printer.Print("<layout>default</layout>\n");
	printer.Outdent();
	printer.Print("</repository>\n");
	printer.Outdent();
	printer.Print("</repositories>\n");
	printer.Print("<build>\n");
	printer.Indent();
	printer.Print("<plugins>\n");
	printer.Indent();
	printer.Print("<plugin>\n");
	printer.Indent();
	printer.Print("<groupId>org.apache.maven.plugins</groupId>\n");
	printer.Print("<artifactId>maven-compiler-plugin</artifactId>\n");
	printer.Print("<version>2.3.2</version>\n");
	printer.Print("<configuration>\n");
	printer.Indent();
	printer.Print("<source>1.6</source>\n");
	printer.Print("<target>1.6</target>\n");
	printer.Outdent();
	printer.Print("</configuration>\n");
	printer.Outdent();
	printer.Print("</plugin>\n");
	printer.Outdent();
	printer.Print("</plugins>\n");
	printer.Outdent();
	printer.Print("</build>\n");
	printer.Outdent();
	printer.Print("</project>\n");
}

bool RevAjaxDwrServicePomXmlCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

              std::string output_filename ("pom.xml");

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
	RevAjaxDwrServicePomXmlCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
