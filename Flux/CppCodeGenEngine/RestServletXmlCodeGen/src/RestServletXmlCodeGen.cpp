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

class RestServletXmlCodeGen: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
		
	public:

		RestServletXmlCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};


void RestServletXmlCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {
            std::string name=file.package();
            size_t pos=name.find_last_of('.');
            std::string controller_package=name.substr(0,pos);
            printer.Print("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
            printer.Print("<beans xmlns=\"http://www.springframework.org/schema/beans\"\n");
            printer.Indent();
            printer.Print("xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:context=\"http://www.springframework.org/schema/context\"\n");
            printer.Print("xmlns:jee=\"http://www.springframework.org/schema/jee\" xmlns:aop=\"http://www.springframework.org/schema/aop\"\n");
            printer.Print("xmlns:tx=\"http://www.springframework.org/schema/tx\" xmlns:p=\"http://www.springframework.org/schema/p\"\n");
            printer.Print("xsi:schemaLocation=\"http://www.springframework.org/schema/beans\n");
            printer.Print("http://www.springframework.org/schema/beans/spring-beans-2.5.xsd\n");
            printer.Print("http://www.springframework.org/schema/jee\n");
            printer.Print("http://www.springframework.org/schema/jee/spring-jee.xsd\n");
            printer.Print("http://www.springframework.org/schema/tx\n");
            printer.Print("http://www.springframework.org/schema/tx/spring-tx-2.5.xsd\n");
            printer.Print("http://www.springframework.org/schema/context\n");
            printer.Print("http://www.springframework.org/schema/context/spring-context-2.5.xsd\">\n");
            printer.Print("<context:component-scan base-package=\"`controller_package`.controller\" />\n","controller_package",controller_package);
            printer.Print("<!-- To enable @RequestMapping process on type level and method level -->\n");
            printer.Print("<bean class=\"org.springframework.web.servlet.mvc.annotation.DefaultAnnotationHandlerMapping\" />\n");
            printer.Print("<bean class=\"org.springframework.web.servlet.mvc.annotation.AnnotationMethodHandlerAdapter\" />\n");
            printer.Print(" <!--	\n");
            printer.Print("<bean class=\"org.springframework.web.servlet.view.ContentNegotiatingViewResolver\">\n");
            printer.Print("<property name=\"mediaTypes\">\n");
            printer.Print("<map>\n");
            printer.Print("<entry key=\"xml\" value=\"application/xml\" />\n");
            printer.Print("<entry key=\"html\" value=\"text/html\" />\n");
            printer.Print("</map>\n");
            printer.Print("</property>\n");
            printer.Print("<property name=\"viewResolvers\">\n");
            printer.Print("<list>\n");
            printer.Print("<bean class=\"org.springframework.web.servlet.view.BeanNameViewResolver\" />\n");
            printer.Indent();
            printer.Print("<bean id=\"viewResolver\" class=\"org.springframework.web.servlet.view.UrlBasedViewResolver\">\n");
            printer.Indent();
            printer.Print("<property name=\"viewClass\"\n");
            printer.Print("     value=\"org.springframework.web.servlet.view.JstlView\" />\n");
            printer.Print("<property name=\"prefix\" value=\"/WEB-INF/jsp/\" />\n");
            printer.Print("<property name=\"suffix\" value=\".jsp\" />\n");
            printer.Outdent();
            printer.Print("</bean>\n");
            printer.Print("</list>\n");
            printer.Print("</property>\n");
            printer.Outdent();
            printer.Print("</bean>\n");
            printer.Print("-->\n");
            printer.Outdent();
            printer.Print("</beans>\n");

	
}


bool RestServletXmlCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

	std::string output_filename ("rest-servlet.xml");

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
	RestServletXmlCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
