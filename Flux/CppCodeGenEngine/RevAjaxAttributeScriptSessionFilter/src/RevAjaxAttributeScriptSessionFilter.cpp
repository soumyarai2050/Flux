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

class RevAjaxAttributeScriptSessionFilter: public FluxCodeGenerator {
	protected:

		
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
		
	public:

		RevAjaxAttributeScriptSessionFilter(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

void RevAjaxAttributeScriptSessionFilter::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {
	
      bool notifyAnnotation=isReverseAjaxEnable(file); 
      if(notifyAnnotation)
      {
               std::string package=file.package();
               size_t pos = package.find_first_of('.');
               std::string name = package.substr(0,pos);
               printer.Print(" package `name`.dwr.reverseajax;\n","name",name);
               printer.Print("import org.directwebremoting.ScriptSession;\n");
               printer.Print("import org.directwebremoting.ScriptSessionFilter;\n");
               printer.Print("public class AttributeScriptSessionFilter implements ScriptSessionFilter\n{\n");
               printer.Indent();
               printer.Print(" public final static String SCRIPT_SESSION_ATTR = \"SCRIPT_SESSION_ATTR\";\n");
               printer.Print("private final String attributeName;\n");
               printer.Print("public AttributeScriptSessionFilter(String attributeName)\n");
               printer.Print(" {\n");
               printer.Indent();
               printer.Print("     this.attributeName = attributeName;\n");
               printer.Outdent();
               printer.Print(" }\n");
               printer.Print("  @Override\n");
               printer.Print(" public boolean match(ScriptSession session)\n");
               printer.Print(" {\n");
               printer.Indent();
               printer.Print("     Object check = session.getAttribute(attributeName);\n");
               printer.Print("    return (check != null && check.equals(Boolean.TRUE));\n");
               printer.Outdent();
               printer.Print("  }\n");
               printer.Outdent();
               printer.Print("}\n");
      }
    
}



bool RevAjaxAttributeScriptSessionFilter::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
		 //This gives only until com
         std::string package=file->package();
         size_t pos = package.find_first_of('.');
         std::string name = package.substr(0,pos);
         std::string output_filename (name+"/dwr/reverseajax/AttributeScriptSessionFilter.java" );

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
	RevAjaxAttributeScriptSessionFilter generator;
	return PluginMain(argc, argv, &generator);
}
