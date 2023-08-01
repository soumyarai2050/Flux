/**
 * Protocol Buffer CPP Test Code Generator Plugin for protoc
 * By Dev-3
 *
 */
#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include<set>
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;
class FinalWebXmlCodeGen : public FluxCodeGenerator 
{
	protected:
		void PrintMessages(io::Printer &printer, const FileDescriptor & file) const;
	public:
		FinalWebXmlCodeGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void FinalWebXmlCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
{
	map<std::string,std::string> variables;
	variables["project_name"]=GetProjectName();
	std::string fileName=file.package();
	size_t pos = fileName.find_first_of ('.');
	variables["listener_package"]=fileName.substr(0,pos)+".listener."+variables["project_name"]+"ServiceListener";
	printer.Indent();
	//printer.Print("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
	printer.Print("<web-app xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n ");
	printer.Print("xmlns=\"http://java.sun.com/xml/ns/javaee\" xmlns:web=\"http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd\" \n");
	printer.Print("xsi:schemaLocation=\"http://java.sun.com/xml/ns/javaee http://java.sun.com/xml/ns/javaee/web-app_3_0.xsd\"\n");
	printer.Print("id=\"WebApp_ID\" version=\"3.0\">\n");
	printer.Print("<display-name>ProtoBufTest</display-name>\n");
	printer.Print("<welcome-file-list>\n");
	printer.Print("	<welcome-file>index.html</welcome-file>\n\n");
	printer.Print("	\t<welcome-file>index.htm</welcome-file>\n");
	printer.Print("	\t<welcome-file>index.jsp</welcome-file>\n");
	printer.Print("	\t<welcome-file>default.html</welcome-file>\n");
	printer.Print("	\t<welcome-file>default.htm</welcome-file>\n");
	printer.Print("	\t<welcome-file>default.jsp</welcome-file>\n");
	printer.Print("	</welcome-file-list>\n\n");
	printer.Print("	<context-param>\n\n");
	printer.Print("	\t<param-name>contextConfigLocation</param-name>\n");
	printer.Print("	\t<param-value>\n");
	printer.Print("	   \t/WEB-INF/spring/*-SpringConfig.xml\n");
	printer.Print("           \t/WEB-INF/rest-servlet.xml\n");
	printer.Print("	\t</param-value>\n");
	printer.Print("	</context-param>\n\n");
	printer.Print("	<listener>\n");
	printer.Print("	\t<listener-class>org.springframework.web.context.ContextLoaderListener</listener-class>\n");
	printer.Print("	</listener>\n\n");
	printer.Print("	<listener>\n");
	printer.Print("	\t<listener-class>");
	printer.Print(variables,"`listener_package`");
	printer.Print("</listener-class>\n");
	printer.Print("	</listener>\n\n");
	printer.Print("	\t<servlet>\n");
	printer.Print("	  \t<servlet-name>dwr-invoker</servlet-name>\n");
	printer.Print("	  \t<servlet-class>org.directwebremoting.servlet.DwrServlet</servlet-class>\n\n");
	printer.Print("	\t\t<init-param>\n");
	printer.Print("	\t\t  <param-name>debug</param-name>\n");
	printer.Print("	\t\t  <param-value>false</param-value>\n");
	printer.Print("	\t\t</init-param>\n\n");
	printer.Print("	\t\t<init-param>\n");
	printer.Print("	\t\t  <param-name>logLevel</param-name>\n");
	printer.Print("	\t\t  <param-value>ERROR</param-value>\n");
	printer.Print("	\t\t</init-param>\n\n");
	printer.Print("	\t\t<init-param>\n");
	printer.Print("	\t\t  <param-name>allowScriptTagRemoting</param-name>\n");
	printer.Print("	\t\t  <param-value>true</param-value>\n");
	printer.Print("	\t\t</init-param>\n\n");
	printer.Print("	\t\t<init-param>\n");
	printer.Print("	\t\t  <param-name>crossDomainSessionSecurity</param-name>\n");
	printer.Print("	\t\t  <param-value>false</param-value>\n");
	printer.Print("	\t\t</init-param>\n\n");
	printer.Print("             <init-param>\n");
	printer.Print("              \t\t<param-name>activeReverseAjaxEnabled</param-name>\n");
	printer.Print("              \t\t<param-value>true</param-value>\n");
	printer.Print("               </init-param>\n");
	printer.Print("	\t</servlet>\n\n");

	/**/
	printer.Print("      <servlet>\n");
	printer.Print("        <servlet-name>rest</servlet-name>\n");
	printer.Print("        <servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>\n");
	printer.Print("        <load-on-startup>1</load-on-startup>\n");
	printer.Print("      </servlet>\n");
	/**/
	printer.Print("	\t<servlet-mapping>\n");
	printer.Print("	\t  <servlet-name>dwr-invoker</servlet-name>\n");
	printer.Print("	\t  <url-pattern>/dwr/*</url-pattern>\n");
	printer.Print("	\t</servlet-mapping>\n");
	/**/
	printer.Print("     <servlet-mapping>\n");
	printer.Print("        <servlet-name>rest</servlet-name>\n");
	printer.Print("        <url-pattern>/service/*</url-pattern>\n");
	printer.Print("     </servlet-mapping>\n");
	/**/
	printer.Print("	</web-app>\n\n");
	printer.Outdent();
}

bool FinalWebXmlCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

	std::string output_filename ("web.xml");

	// Generate main file.
	scoped_ptr<io::ZeroCopyOutputStream> output(
		output_directory->Open(output_filename)
	);

	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}
int main(int argc, char* argv[]) 
   {
        if(getenv("DEBUG_ENABLE"))
                sleep(30);
	FinalWebXmlCodeGen generator;
	return PluginMain(argc, argv, &generator);
   }
