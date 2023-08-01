/**
 * Protocol Buffer CPP Test Code Generator Plugin for protoc
 * By Dev-1
 *
 */
#include<list>
#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class RevAjaxDwrDataPrintOrCreateAndPopulate : public FluxCodeGenerator 
{
	protected:
		void PrintGetterMethod(io::Printer &printer, const Descriptor & message,const std::string &prefix) const;
		void PrintMessage(io::Printer &printer, const Descriptor & message) const;
		void PrintComplexMessage(io::Printer &printer, const Descriptor & message, 
										const std::string& prefix, bool isGetter = true) const;
		void PrintMessages(io::Printer &printer, const FileDescriptor & file) const;
		std::string VariableGetterName(const FieldDescriptor & field) const;
		std::string VariableSetterName(const FieldDescriptor & field) const;
	public:
		RevAjaxDwrDataPrintOrCreateAndPopulate(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};



std::string RevAjaxDwrDataPrintOrCreateAndPopulate::VariableGetterName(const FieldDescriptor & field) const {
	return (std::string("get") +UnderscoresToCapitalizedCamelCase(field));
}

std::string RevAjaxDwrDataPrintOrCreateAndPopulate::VariableSetterName(const FieldDescriptor & field) const {
	return (std::string("set") +UnderscoresToCapitalizedCamelCase(field));
}

std::string CamelCaseToLower(const std::string& input) {
   std::string result;
   for (size_t i = 0; i < input.size(); i++) {
       // Force all letter to lower-case 
      if ('A' <= input[i] && input[i] <= 'Z') {
           result += input[i] + ('a' - 'A');
      }
      else {
            result+=input[i];
      }
   }
   return result;
}

void RevAjaxDwrDataPrintOrCreateAndPopulate::PrintGetterMethod(io::Printer &printer, const Descriptor & message ,const std::string &prefix) const
{
  
    static char counterVar[3] = {'a','a','\0'};
      if('z' == counterVar[1])
	{
		if('z' == counterVar[0])
		{
			//Reset to prevent overflow
			counterVar[0] = 'a';
			counterVar[1] = 'a';
		}
		else
		{
			counterVar[0]++;
		}
	}
	else
	{
		counterVar[1]++;
	}
	
	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		const FieldDescriptor &field ( *message.field(i) );
                map<std::string, std::string> variables;
		variables["name"]             = VariableName(field);
		variables["capitalized_name"] = UnderscoresToCapitalizedCamelCase(field);
		variables["actual_name"]      = UnderscoresToCamelCase(field);
		variables["default"]          = DefaultValueAsString(field);
		variables["comment"]          = field.DebugString();
		variables["getter_name"]      = VariableGetterName(field);
		variables["setter_name"]      = VariableSetterName(field);
		variables["prefix"]           = prefix;
		variables["DummyVal"]	      = TestValueAsString(field);
		variables["counterVar"]	      = counterVar;
                variables["name"]             = VariableName(field);

                if (field.type() == FieldDescriptor::TYPE_GROUP) 
		{
			size_t p = variables["comment"].find ('{');
			if (p != std::string::npos)
				variables["comment"].resize (p - 1);
		}
		
		switch (field.type()) 
		{
			case FieldDescriptor::TYPE_MESSAGE:
			case FieldDescriptor::TYPE_GROUP:
			variables["type"] = ClassName(*field.message_type()) + " ";
			isComplex = true;
			break;
			default:variables["type"] = "";
		}


                if (field.is_repeated()) 
		{     
                        printer.Print(variables,"LOG.info(\"\");\n");
                        printer.Print(variables,"LOG.info(\"Printing Repeated field `name`\");\n");
			printer.Print(variables,"LOG.info(\"---------------------------------------------\");");
			printer.Print(variables,"\nfor (int `counterVar` = 0; `counterVar` < ");
                        printer.Print(variables,"`prefix`.`getter_name`Count(); `counterVar`++)\n{\n");
                        printer.Indent();
                        if(!isComplex)
                           printer.Print(variables,"");

                        if(isComplex)
                        {
                           std::string childPrefix = prefix +"."+ VariableGetterName(field) + "(" + counterVar + ")";
                           PrintGetterMethod(printer,*field.message_type(),childPrefix);
                        }
                        else
                        {
                           printer.Print(variables,"LOG.info(\"\"+`prefix`.`getter_name`(`counterVar`));\n");
                         
                        }
                                     
                        printer.Outdent();       
                        printer.Print(variables,"\n}\n");  
                }
                else 
		{  
			if(isComplex)
			{
				std::string childPrefix = prefix +"."+VariableGetterName(field) + "()";
				PrintGetterMethod(printer,*field.message_type(),childPrefix);
			}
			else
			{
                              printer.Print(variables,"LOG.info(\"`name` = \" +`prefix`.`getter_name`());\n");
			}
		}

	}
              
}




void RevAjaxDwrDataPrintOrCreateAndPopulate::PrintMessage(io::Printer &printer, const Descriptor & message) const 
{
   std::string prefix = std::string ("") + CamelCaseToLower(UnqualifiedClassOrEnumOrFieldName(message));
   printer.Print("\npublic void print`FunName`(`className` `object`)\n{\n","FunName",UnqualifiedClassOrEnumOrFieldName(message),"className",ClassName(message),"object",CamelCaseToLower(UnqualifiedClassOrEnumOrFieldName(message)));
    printer.Print("try\n{\nif (LOG.isInfoEnabled()) {\n");  
   printer.Indent();
   PrintGetterMethod(printer,message,prefix);
   printer.Outdent();
   printer.Print("\n}\n}\n");
   printer.Print("\ncatch (Exception ex) {");
   printer.Print("\nif (LOG.isInfoEnabled()) {");
   printer.Print("\nLOG.info(\"cought by beanGenarator() catch \");");
   printer.Print("\n}\n}");
   printer.Print("\n}\n");
}

void RevAjaxDwrDataPrintOrCreateAndPopulate::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {

            std::string cpp_filename ( file.name());
            size_t slashposition=cpp_filename.find_last_of ('/');
            size_t pos1 = cpp_filename.find_first_of ('.');
            std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
            size_t pos = sbstring.find_first_of ('.');
            std::string file_name=sbstring.substr(0,pos);
             //find package name for the java file generated
            std::string package=file.package();
            size_t p = package.find_last_of('.');
            std::string name = package.substr(0,p);
            printer.Print("package  `name`.dataprintorpopulate;\n\n","name",name);
            printer.Print("import org.slf4j.Logger;\n");
            printer.Print("import org.slf4j.LoggerFactory;\n");

            printer.Print("public class `name`DataPrintOrPopulate {\n","name",file_name);
            printer.Print("private static final Logger LOG = LoggerFactory.getLogger(`name`DataPrintOrPopulate.class);\n","name",file_name);
            printer.Indent();
            for (int i = 0; i < file.message_type_count(); ++i) 
               {
                 PrintMessage(printer, *file.message_type(i));
               }
            printer.Outdent();
            printer.Print("\n}\n");
        
}


bool RevAjaxDwrDataPrintOrCreateAndPopulate::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	scoped_ptr<io::ZeroCopyOutputStream> output(
	output_directory->Open(GetPackageDirectoryName(file) + "/dataprintorpopulate/" + GetFileNameFromFileDescriptor(file) + "DataPrintOrPopulate.java")
	);

	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}


int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	RevAjaxDwrDataPrintOrCreateAndPopulate generator;
	return PluginMain(argc, argv, &generator);
}
