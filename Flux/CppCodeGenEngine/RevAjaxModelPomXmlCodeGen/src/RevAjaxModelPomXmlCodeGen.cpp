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

class RevAjaxModelPomXmlCodeGen: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
		
	public:

		RevAjaxModelPomXmlCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

void RevAjaxModelPomXmlCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
{
      printer.Print("<project xmlns=\"http://maven.apache.org/POM/4.0.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n");
      printer.Print("         xsi:schemaLocation=\"http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd\">\n");
      printer.Print("<modelVersion>4.0.0</modelVersion>\n\n");
      printer.Print("<groupId>project_model</groupId>\n");
      printer.Print("<artifactId>project_model</artifactId>\n");
      printer.Print("<version>0.0.1-SNAPSHOT</version>\n");
      printer.Print("<packaging>jar</packaging>\n\n");
      printer.Print("<name>project_model</name>\n\n");
      printer.Print("<properties>\n");
      printer.Indent();
      printer.Print("<endorsed.dir>${project.build.directory}/endorsed</endorsed.dir>\n");
      printer.Print("<project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>\n");
      printer.Outdent();
      printer.Print("</properties>\n\n");
      printer.Print("<dependencies>\n");
      printer.Indent();
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
      printer.Print("<groupId>ch.qos.logback</groupId>\n");
      printer.Print("<artifactId>logback-classic</artifactId>\n");
      printer.Print("<version>0.9.18</version>\n");
      printer.Outdent();
      printer.Print("</dependency>\n");
      printer.Print("<dependency>\n");
      printer.Indent();
      printer.Print("<groupId>com.google.protobuf</groupId>\n");
      printer.Print("<artifactId>protobuf-java</artifactId>\n");
      printer.Print("<version>2.4.1</version>\n");
      printer.Outdent();
      printer.Print("</dependency>\n");
      printer.Outdent();
      printer.Print("</dependencies>\n\n");
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
      printer.Print("<compilerArguments>\n");
      printer.Indent();
      printer.Print("<endorseddirs>${endorsed.dir}</endorseddirs>\n");
      printer.Outdent();
      printer.Print("</compilerArguments>\n");
      printer.Outdent();
      printer.Print("</configuration>\n");
      printer.Outdent();
      printer.Print("</plugin>\n");
      printer.Print("<plugin>");
      printer.Indent();
      printer.Print("<groupId>org.apache.maven.plugins</groupId>\n");
      printer.Print("<artifactId>maven-war-plugin</artifactId>\n");
      printer.Print("<version>2.1.1</version>\n");
      printer.Print("<configuration>\n");
      printer.Indent();
      printer.Print("<failOnMissingWebXml>false</failOnMissingWebXml>\n");
      printer.Outdent();
      printer.Print("</configuration>\n");
      printer.Outdent();
      printer.Print("</plugin>\n");
      printer.Print("<plugin>\n");
      printer.Indent();
      printer.Print("<groupId>org.apache.maven.plugins</groupId>\n");
      printer.Print("<artifactId>maven-dependency-plugin</artifactId>\n");
      printer.Print("<version>2.1</version>\n");
      printer.Print("<executions>\n");
      printer.Indent();
      printer.Print("<execution>\n");
      printer.Indent();
      printer.Print("<phase>validate</phase>\n");
      printer.Print("<goals>\n");
      printer.Indent();
      printer.Print("<goal>copy</goal>\n");
      printer.Outdent();
      printer.Print("</goals>\n");
      printer.Print("<configuration>\n");
      printer.Indent();
      printer.Print("<outputDirectory>${endorsed.dir}</outputDirectory>\n");
      printer.Print("<silent>true</silent>\n");
      printer.Print("<artifactItems>\n");
      printer.Indent();
      printer.Print("<artifactItem>\n");
      printer.Indent();
      printer.Print("<groupId>javax</groupId>\n");
      printer.Print("<artifactId>javaee-endorsed-api</artifactId>\n");
      printer.Print("<version>6.0</version>\n");
      printer.Print("<type>jar</type>\n");
      printer.Outdent();
      printer.Print("</artifactItem>\n");
      printer.Outdent();
      printer.Print("</artifactItems>\n");
      printer.Outdent();
      printer.Print("</configuration>");
      printer.Outdent();
      printer.Print("</execution>\n");
      printer.Outdent();
      printer.Print("</executions>\n");
      printer.Outdent();
      printer.Print("</plugin>\n");
      printer.Outdent();
      printer.Print("</plugins>\n");
      printer.Print("<pluginManagement>\n");
      printer.Indent();
      printer.Print("<plugins>\n");
      printer.Indent();
      printer.Print("<!--This plugin's configuration is used to store Eclipse m2e settings only. It has no influence on the Maven build itself.-->\n");
      printer.Indent();
      printer.Print("<plugin>\n");
      printer.Indent();
      printer.Print("<groupId>org.eclipse.m2e</groupId>\n");
      printer.Print("<artifactId>lifecycle-mapping</artifactId>\n");
      printer.Print("<version>1.0.0</version>\n");
      printer.Print("<configuration>\n");
      printer.Indent();
      printer.Print("<lifecycleMappingMetadata>\n");
      printer.Indent();
      printer.Print("<pluginExecutions>\n");
      printer.Indent();
      printer.Print("<pluginExecution>\n");
      printer.Indent();
      printer.Print("<pluginExecutionFilter>\n");
      printer.Indent();
      printer.Print("<groupId>\n");
      printer.Indent();
      printer.Print("org.apache.maven.plugins\n");
      printer.Outdent();
      printer.Print("</groupId>\n");
      printer.Print(" <artifactId>\n");
      printer.Indent();
      printer.Print("maven-dependency-plugin\n");
      printer.Outdent();
      printer.Print("</artifactId>\n");
      printer.Print("<versionRange>\n");
      printer.Print("\t\t[2.1,)\n");
      printer.Print("</versionRange>\n");
      printer.Print("<goals>\n");
      printer.Indent();
      printer.Print("<goal>copy</goal>\n");
      printer.Outdent();
      printer.Print("</goals>\n");
      printer.Outdent();
      printer.Print("</pluginExecutionFilter>\n");
      printer.Print("<action>\n");
      printer.Indent();
      printer.Print("<ignore></ignore>\n");
      printer.Outdent();
      printer.Print("</action>\n");
      printer.Outdent();
      printer.Print("</pluginExecution>\n");
      printer.Outdent();
      printer.Print("</pluginExecutions>\n");
      printer.Outdent();
      printer.Print("</lifecycleMappingMetadata>\n");
      printer.Outdent();
      printer.Print("</configuration>\n");
      printer.Outdent();
      printer.Print("</plugin>\n");
      printer.Outdent();
      printer.Print("</plugins>\n");
      printer.Outdent();
      printer.Print("</pluginManagement>\n");
      printer.Outdent();
      printer.Print("</build>\n");
      printer.Outdent();
      printer.Print("</project>\n");
      
}

bool RevAjaxModelPomXmlCodeGen::Generate(const FileDescriptor* file,
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
	RevAjaxModelPomXmlCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
