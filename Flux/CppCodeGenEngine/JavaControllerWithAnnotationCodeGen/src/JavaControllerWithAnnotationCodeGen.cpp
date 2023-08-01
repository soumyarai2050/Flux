/**
 * Protocol Buffer CPP Test Code Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class JavaControllerWithAnnotationCodeGen : public FluxCodeGenerator {
		protected:
		void PrintControllerMethod(io::Printer &printer, const Descriptor & message,std::string & file_name) const;
 		void PrintMessages(io::Printer &printer, const FileDescriptor & file) const;

                public:
		JavaControllerWithAnnotationCodeGen(){}
  		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};


std::string CamelCaseConvertor(const std::string& input, bool cap_next_letter) {
  std::string result;
  // Note:  I distrust ctype.h due to locales.
  for (size_t i = 0; i < input.size(); i++) {


 if ('A' <= input[i] && input[i] <= 'Z') {
      if (!cap_next_letter) {
        // Force all letter to lower-case 
        result += input[i] + ('a' - 'A');
      } else if(i==0){
        // change only first letter into lower-case other left as-is.
           result += input[i] + ('a' - 'A');
       } else {
         result+=input[i];
       }

      }else{
         result+=input[i];
      }
   }
  return result;
}

void JavaControllerWithAnnotationCodeGen::PrintControllerMethod(io::Printer &printer, const Descriptor & message,std::string &file_name) const 
{
	std::string strResponse = message.options().GetExtension(FluxMsgRsp);
	if(0 != strResponse.length() && strResponse!="!")
	{
		map<std::string,std::string>variables;
		variables["msg_name"]            =    UnderscoresToCapitalizedCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
		variables["msg_obj_name"]        =    UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
		variables["res_class_name"]      =    UnderscoresToCapitalizedCamelCase(strResponse);
		variables["res_obj_name"]        =    UnderscoresToCamelCase(strResponse);
		variables["service_name"]        =    UnderscoresToCapitalizedCamelCase(file_name);
		variables["service_obj_name"]    =    UnderscoresToCamelCase(file_name);
		printer.Indent();  
		printer.Print(variables,"\n\n@RequestMapping(method = RequestMethod.POST, value = \"/`msg_obj_name`\")\n");
		printer.Print(variables,"public void `msg_obj_name`(HttpServletRequest request,HttpServletResponse response)\n");
		printer.Print("{\n");
		printer.Indent();
		printer.Print("try \n");
		printer.Print("{\n");
		printer.Indent();
		printer.Print(variables,"`msg_name`Dto `msg_obj_name`Dto=new `msg_name`Dto();\n");
		printer.Print(variables,"`msg_obj_name`Dto.parseFrom(request.getInputStream());\n");
		printer.Print("ApplicationContext context = WebApplicationContextUtils.getWebApplicationContext(request.getServletContext());\n");
		printer.Print(variables,"I`service_name` `service_obj_name`=(I`service_name`)context.getBean(\"`service_obj_name`\");\n");
		printer.Print(variables,"`res_class_name`Dto `res_obj_name`Dto= `service_obj_name`.`msg_obj_name`Dto(`msg_obj_name`Dto);\n");
		printer.Print(variables,"`res_class_name` resposeBuilder = `res_obj_name`Dto.createProtoBufObj();\n");
		printer.Print(variables,"resposeBuilder.writeTo(response.getOutputStream());\n");
		printer.Print(variables,"response.setHeader(\"Accept\", \"X-Protobuf-Schema\");\n");
		printer.Print("if (LOG.isDebugEnabled())\n");
		printer.Print("{\n");
		printer.Print("  LOG.trace(\">> fun()\");\n");
		printer.Print(variables,"  LOG.debug(\"`msg_obj_name` request object caught\");\n");
		printer.Print("}\n");
		printer.Outdent();
		printer.Print("}\n");
		printer.Print("catch (Exception ex) \n");
		printer.Print("{\n ");
		printer.Print("        LOG.trace(\">> fun()\");\n");
		printer.Print("        LOG.error(\"Exception caught \", ex);\n");
		printer.Print("}\n");
		printer.Outdent();
		printer.Print("}\n");
		printer.Outdent();
	}
}


void JavaControllerWithAnnotationCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {
   std::string cpp_filename ( file.name());
   size_t pos1 = cpp_filename.find_last_of ('/');
   size_t pos2 = cpp_filename.find_first_of ('.');
   std::string name = cpp_filename.substr(pos1+1,pos2);
   pos2 = name.find_first_of ('.');
   name = name.substr(0,pos2);
   pos2=file.package().find_last_of ('.');
   std::string service_package=file.package().substr(0,pos2)+".services.impl."+name+"TestImpl";
   std::string controller_package=file.package().substr(0,pos2);

   printer.Print("package `controller_package`.controller;\n","controller_package",controller_package);
   printer.Print("import `controller_package`.services.*;\n","controller_package",controller_package);
   printer.Print( "import `package`.*;\n","package",file.package());
   printer.Print( "import `package`.dto.*;\n","package",file.package());
   printer.Print( "import `package`;\n","package",service_package);
   printer.Print( "import javax.servlet.http.HttpServletRequest;\n");
   printer.Print( "import javax.servlet.http.HttpServletResponse;\n");
   printer.Print( "import  org.springframework.stereotype.Controller;\n");
   printer.Print("import org.springframework.context.ApplicationContext;\n");
   printer.Print("import org.springframework.web.context.support.WebApplicationContextUtils;\n");
   printer.Print( "import org.springframework.web.bind.annotation.RequestMapping;\n");
   printer.Print( "import org.springframework.web.bind.annotation.RequestMethod;\n");
   printer.Print( "import org.slf4j.Logger;\n");
   printer.Print( "import org.slf4j.LoggerFactory;\n");
   printer.Print("\n@Controller\n");
   printer.Print("public class `name`Controller{\n","name",UnderscoresToCapitalizedCamelCase(name));
   printer.Print("   private static final Logger LOG=LoggerFactory.getLogger(`name`Controller.class);","name",UnderscoresToCapitalizedCamelCase(name));
   for (int i = 0; i < file.message_type_count(); ++i) {
		PrintControllerMethod(printer, *file.message_type(i),name);
   }
   printer.Print( "\n}");
}
bool JavaControllerWithAnnotationCodeGen::Generate(const FileDescriptor* file,const std::string& parameter,
                                                   OutputDirectory* output_directory,std::string* error) const 
{
	scoped_ptr<io::ZeroCopyOutputStream> output(
	output_directory->Open(GetPackageDirectoryName(file) + "/controller/" + GetFileNameFromFileDescriptor(file) + "Controller.java")
	);

	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}


int main(int argc, char* argv[])
 {
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	JavaControllerWithAnnotationCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
