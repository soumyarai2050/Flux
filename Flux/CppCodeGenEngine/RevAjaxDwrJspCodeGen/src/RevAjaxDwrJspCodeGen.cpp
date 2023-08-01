/**
 * Protocol Buffer CPP Test Code Generator Plugin for protoc
 * By Dev-2
 */
#include<list>
#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <map>
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;
class RevAjaxDwrJspCodeGen : public FluxCodeGenerator 
{
	protected:
         void PrintJspBodyData(io::Printer &printer, const Descriptor & message,const std::string &prefix,const FileDescriptor & file) const;
         void PrintJspComplexMessage(io::Printer &printer, const Descriptor & message, const std::string &prefix,const std::string &childprefix) const ;
         void PrintJspShowResult(io::Printer &printer, const Descriptor & message ,const std::string &prefix) const;
		 void PrintJspRepNormalFields(io::Printer &printer, const Descriptor & message, const std::string &prefix) const ;
         void PrintJspFunctionMain(io::Printer &printer, const Descriptor & message, const std::string &prefix) const ;
         void PrintMessage(io::Printer &printer, const Descriptor & message ,const std::string &strResponse,const FileDescriptor & file) const ;
         void PrintMessages(const FileDescriptor & file,OutputDirectory& output_directory) const ;
         std::string VariableGetterName(const FieldDescriptor & field) const;
	public:
         mutable list<std::string>mylist;
          mutable list<std::string>myfieldlist;
         RevAjaxDwrJspCodeGen(){}
         bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

std::string RevAjaxDwrJspCodeGen::VariableGetterName(const FieldDescriptor & field) const 
{
	return (std::string("get") + UnderscoresToCapitalizedCamelCase(field));
}

std::string CamelCaseToLower(const std::string& input) 
{
	std::string result;
	for (size_t i = 0; i < input.size(); i++) 
	{
		// Force all letter to lower-case 
		if ('A' <= input[i] && input[i] <= 'Z') 
        {
           result += input[i] + ('a' - 'A');
        }
		else 
        {
           result+=input[i];
        }
	}
	return result;
}
   
void RevAjaxDwrJspCodeGen:: PrintJspRepNormalFields(io::Printer &printer, const Descriptor & message, const std::string &prefix) const 
{
	//To Print Repeated normal  
	for (int i = 0; i < message.field_count(); ++i)
    {      
        const FieldDescriptor &field ( *message.field(i) );
        if( field.is_repeated() && field.type() != FieldDescriptor::TYPE_GROUP && field.type() != FieldDescriptor::TYPE_MESSAGE )
        {    
            std::string var_name=VariableName(field);
            char z=0;    
            int counter=0;
            for (list<std::string>::iterator it=mylist.begin();it!=mylist.end();++it)
            if(*it==VariableName(field)) counter+=1;
            if(counter>1)
            {
                z=63+counter;
                std::string s(&z,1);
				var_name=VariableName(field)+s;
            }
            printer.Print("var fieldobj`suffix` = document.getElementsByName(\"`name`\");\n","name",var_name,"suffix",prefix);
            printer.Print("var `name``suffix` = new Array();\n","name",VariableName(field),"suffix",prefix);
            printer.Print("for ( var i = 0; i < fieldobj`suffix`.length; i++) {\n","suffix",prefix);
            printer.Print("  	if (fieldobj`suffix`[i].checked)\n{","suffix",prefix);
            printer.Print(" var phid ={\"`name`\":fieldobj`suffix`[i].value};","name",VariableName(field),"suffix",prefix);
            printer.Print("		`name``suffix`.push(phid);\n}","name",VariableName(field),"suffix",prefix);
            printer.Print("}\n\n");
        }
    }
}

void RevAjaxDwrJspCodeGen::PrintJspFunctionMain(io::Printer &printer, const Descriptor & message, const std::string &prefix) const 
{
	int field_count = message.field_count();

	map <std::string,std::string>variables;
	variables["field_sep"] = ",";
	variables["suffix"]=prefix;
	for (int i = 0; i < field_count ; ++i)
	{ 
		const FieldDescriptor &field (*message.field(i));
		if(i == field_count-1)
		variables["field_sep"] = "";
		variables["field_name"] = VariableName(field);

		if(field.is_repeated())
		{
			if(field.type() == FieldDescriptor::TYPE_GROUP || field.type() == FieldDescriptor::TYPE_MESSAGE)
			{
				printer.Print(variables,"\"`field_name`\" : [ `field_name``suffix`Obj, `field_name``suffix`Obj, `field_name``suffix`Obj, `field_name``suffix`Obj ] `field_sep`\n");
			}
			else
			{
				printer.Print(variables,"\"`field_name`\" : `field_name``suffix` `field_sep`\n");
			}
		}
		else
		{
			if(field.type() == FieldDescriptor::TYPE_GROUP  || field.type() == FieldDescriptor::TYPE_MESSAGE)
			{
				printer.Print(variables,"\"`field_name`\" : `field_name``suffix`Obj `field_sep`\n");
			}
			else
			{
				variables["var_name"]=VariableName(field);
				char a=0;
				int counter=0;
				for (list<std::string>::iterator it=mylist.begin();it!=mylist.end();++it)
				{
					if(*it==VariableName(field))
						counter+=1;
				}
				if(counter>1)
				{
					a=63+counter;
					std::string s(&a,1);
					variables["var_name"]=VariableName(field)+s;
				}
				std::string strFieldHide=field.options().GetExtension(FluxFldHide);
				if(strFieldHide.length() == 0)
				{
					//This field value should come from UI
					printer.Print(variables, "\"`field_name`\" : document.getElementById(\"`var_name`\").value `field_sep`\n");
				}
				else
				{
					//This is hidden field value should be generated
					variables["DummyVal"] = TestValueAsString(field,true,true);
					if(XmlDataType(field)=="String")
					{
						std::string temp=variables["DummyVal"];
						size_t pos=temp.find_last_of("\"");
						variables["DummyVal"]=temp.substr(1,pos-1);
					}
					else if(XmlDataType(field)=="Enumeration")
					{
						const EnumDescriptor &enum1 (*field.enum_type());
						const EnumValueDescriptor &ev (*enum1.value(1));//Always return 2nd (starts from 0) value as enum test value
						variables["DummyVal"]=ev.name();
					}
					printer.Print(variables, "\"`field_name`\" : \"`DummyVal`\" `field_sep`\n");
				}
			}
		}
	}
}

//STEP 1- FOR APPLYONG UNIQUESS RULE PREFIX AND CHILD PREFIX IS USED
//STEP 2- TRAVERSE ALL FIELDS IN RECIEVED MESSAGE AND PUSH THEM IN LIST FOR IMPLEMENT UNIQUE COUNTER SUFFIX
//STEP 3 - IF COMPLEX FIELD FOUND 
		// 1- TRAVERSE LIST FOR VARABLE NAME INCREMENT COUNTER FOR SAME NAME IF NAME FOUND MORE THEN ONCE INCREMENT STAIC VARIABLE ct
		// 2- PREFORMING DEPTH FIRST SEARCH FOR COMPLEX FIELDS AND PASS UNIQUE SUFFIX
//STEP 4 - PRINT REPEATED NORMAL FIELDS USING PrintJspRepNormalFields();
//STEP 5 - PRINT VARIABLES OF COMPLEX TYPE AND FILL DATA USING 	PrintJspFunctionMain();
void RevAjaxDwrJspCodeGen::PrintJspComplexMessage(io::Printer &printer, const Descriptor & message, const std::string &prefix,const std::string &childprefix) const 
{
    map<std::string,std::string>variables;
    static int ct=1;
	//STEP 1
	variables["prefix"]=childprefix;
	variables["childprefix"]=SimpleItoa(ct);	
	//STEP -2
    for (int i = 0; i < message.field_count(); ++i)
    {
       const FieldDescriptor &field ( *message.field(i) );
        mylist.push_back(VariableName(field));
        if(field.type() == FieldDescriptor::TYPE_GROUP|| field.type() == FieldDescriptor::TYPE_MESSAGE)
        {   //STEP -3
            int counter=0;
            for (list<std::string>::iterator it=mylist.begin();it!=mylist.end();++it)
            if(*it==VariableName(field)) counter+=1;
            if(counter>1)
            {   //step 3-1 UNIQUE COUNTER
				ct+=1;
            }
     	    const Descriptor & newmessage(*field.message_type());
            //STEP 3-2 PRFORMING DFS FOR NESTED COMPLEX FIELDS RETURN TO STEP -1
            PrintJspComplexMessage(printer,newmessage,variables["prefix"],variables["childprefix"]);
            // POP COMPLEX FIELDS FROM STACK AND TRAVERSING ITS FIELDS
      
            //STEP -4 PRINT REPEATED NORMAL FIELD IF ANY			
            PrintJspRepNormalFields(printer,*field.message_type(),variables["childprefix"]) ;
            //STEP -5 PRINT VARIABLES OF ALL TRAVERSED COMPLEX FIELDS
            printer.Print("var `name``suffix`Obj = {\n","name",VariableName(field),"suffix",variables["prefix"]);
            //FILL DATA FIELDS IN ALL TRAVERSED COMPLEX FIELDS 
            PrintJspFunctionMain(printer,*field.message_type(),variables["childprefix"]);
            printer.Print("};\n\n");
        }
    }
}



void RevAjaxDwrJspCodeGen::PrintJspShowResult(io::Printer &printer, const Descriptor & message ,const std::string &prefix) const
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
		variables["prefix"]           = prefix;
		variables["counterVar"]	      = counterVar;

		switch (field.type()) 
		{
			case FieldDescriptor::TYPE_MESSAGE:
			case FieldDescriptor::TYPE_GROUP:
				variables["type"] = QualifiedJavaClassOrEnumName(*field.message_type()) + " ";
				isComplex = true;
				break;
			default:variables["type"] = "";
		}

		if (field.is_repeated()) 
		{     
			printer.Print(variables,"\nresult = result + \"#################`name`#####################\" + \"</br>\";\n");
			printer.Indent();
			if(!isComplex)
				printer.Print(variables,"");

			if(isComplex)
			{  
				printer.Print(variables,"\nvar `name` = `prefix`.`name`;\n");
				printer.Print(variables,"\nfor (var `counterVar` = 0; `counterVar` < ");
				printer.Print(variables,"`name`.length; `counterVar`++)\n{\n");
				std::string childPrefix = VariableName(field) + "[" + counterVar + "]";
				PrintJspShowResult(printer,*field.message_type(),childPrefix);
				printer.Print(variables,"\n}\n");  
			}
			else
			{
				printer.Print(variables,"result = result + \" `name` = \" + `prefix`.`name` + \"</br>\";\n");
			}
			printer.Outdent();       
		}
		else 
		{  
			if(isComplex)
			{
				std::string childPrefix = prefix +"."+VariableName(field) ;
				PrintJspShowResult(printer,*field.message_type(),childPrefix);
			}
			else
			{
				printer.Print(variables,"result = result + \" `name` = \" + `prefix`.`name` + \"</br>\";\n");
			}
		}
	}
}


void RevAjaxDwrJspCodeGen::PrintMessage(io::Printer &printer, const Descriptor & message,const std::string &strResponse,const FileDescriptor & file) const 
{
	std::string file_name ( file.name());
	size_t slashposition=file_name.find_last_of ('/');
	size_t pos1 = file_name.find_first_of ('.');
	std::string sbstring = file_name.substr(slashposition+1,pos1);
	size_t pos = sbstring.find_first_of ('.');
	file_name=sbstring.substr(0,pos);

	//	printer.Print("`name`\n","name", UnqualifiedClassOrEnumOrFieldName(message));
	printer.Indent();
	map <std::string,std::string>variables;
	variables["class_name"]    =   UnqualifiedClassOrEnumOrFieldName(message); 
	variables["obj_name"]      =   UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
	variables["file_name"]     =   UnderscoresToCamelCase(file_name);
	variables["response"]     =   strResponse;
	printer.Print(variables,"function get`class_name`Dto() \n{\n");
	printer.Indent(); 
	// printing all field variables
	PrintJspComplexMessage(printer,message,"","");
	// to print vaiable for message 
	PrintJspRepNormalFields(printer,message,"") ;
	printer.Print(variables,"var `obj_name` = {\n");
	PrintJspFunctionMain(printer,message,"");
	printer.Print("};\n\n");

	// to print method for access pojo usinf service object
	printer.Print(variables,"`file_name`.`obj_name`Dto(`obj_name`, {\n");
	printer.Print("callback : function(data) {\n");
	printer.Print("         showResult(data);");
	printer.Print("} \n});\n");

	printer.Outdent();
	printer.Print("}\n\n");

	//ONLY PASS RESPONSE TYPE MESSAGE TO SHOW RESULT FUNCTION

	std::string prefix = std::string ("") + CamelCaseToLower(UnqualifiedClassOrEnumOrFieldName(message));
	for (int i = 0; i < file.message_type_count(); ++i) 
	{ 
		// PRINTING SHOW RESULT METHOD
		const Descriptor & newmessage(*file.message_type(i));
		std::string prefix = std::string ("") + CamelCaseToLower(UnqualifiedClassOrEnumOrFieldName(newmessage));

		if(UnqualifiedClassOrEnumOrFieldName(newmessage)==strResponse)
		{
			printer.Print("function showResult(`prefix`)","prefix",prefix); 
			printer.Print("\n{\n");
			printer.Indent();
			printer.Print("var result = \"\";\n");
			PrintJspShowResult(printer,newmessage,prefix);
			printer.Print("document.getElementById(\"resultdiv\").innerHTML = result;");
			printer.Outdent();
			printer.Print("\n}\n");
		}
	}
	printer.Outdent();
}

void RevAjaxDwrJspCodeGen::PrintMessages(const FileDescriptor & file,OutputDirectory& output_directory) const 
{
	std::string cpp_filename ( file.name());
	size_t slashposition=cpp_filename.find_last_of ('/');
	size_t pos1 = cpp_filename.find_first_of ('.');
	std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
	size_t pos = sbstring.find_first_of ('.');
	std::string file_name=sbstring.substr(0,pos);

	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		mylist.clear();
		myfieldlist.clear();
		const Descriptor & message(*file.message_type(i));
		std::string strResponse=ResponseNameCheckerAndGenerator(message);

		if(0 != strResponse.length())
		{
			std::string output_filename =UnqualifiedClassOrEnumOrFieldName(message)+".jsp";
			scoped_ptr<io::ZeroCopyOutputStream> output(output_directory.Open(output_filename));
			io::Printer printer(output.get(), '`');
			printer.Print("<%@ page language=\"java\" contentType=\"text/html; charset=ISO-8859-1\" pageEncoding=\"ISO-8859-1\"%>\n");
			printer.Print("<!DOCTYPE html PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd\">\n");
			printer.Print("<html>\n");
			printer.Print("<head>\n");
			printer.Print(" <meta http-equiv=\"Content-Type\" content=\"text/html; charset=ISO-8859-1\">\n");
			printer.Print("<title>Insert title here</title>\n");
			printer.Print("<script type='text/javascript' src=\"../dwr/util.js\"></script>");
			printer.Print("<script type='text/javascript' src=\"../dwr/engine.js\"></script>\n");
			printer.Print("<script type='text/javascript' src=\"../dwr/interface/`file_name`.js\"></script>\n\n","file_name",UnderscoresToCamelCase(file_name));

			printer.Print("<script type=\"text/javascript\" >\n");

			std::string strNotifyAnnotation=message.options().GetExtension(FluxMsgNotify);
			if(0 != strNotifyAnnotation.length() && strNotifyAnnotation!="!")
			{		
				printer.Print("	window.onload=function()\n");
				printer.Print("	{\n");
				printer.Print("		dwr.engine.setActiveReverseAjax(true); \n");
				printer.Print("		dwr.engine.setErrorHandler(errorHandler); \n");
				printer.Print("		dwr.engine.setNotifyServerOnPageUnload(true);\n");
				printer.Print("		subscribeAlertService();\n");
				printer.Print("	};\n");
				printer.Print("		  \n");
				printer.Print("	function errorHandler(message, ex) {\n");
				printer.Print("		alert(\"Cannot connect to server\");\n");
				printer.Print("	}\n");
				printer.Print("		  \n");
				printer.Print("	function subscribeAlertService() {\n");
				printer.Print("		addressBookService.subscribeAlertService();\n");
				printer.Print("	}\n");
				printer.Print("			  \n");
				printer.Print("	function unSubscribeAlertService() {\n");
				printer.Print("		addressBookService.unSubscribeAlertService();\n");
				printer.Print("	}\n");

				printer.Print("	function reverseAjacResult(result)\n");
				printer.Print("	{\n");
				printer.Print("		  var text = dwr.util.getValue(\"resultdiv\",{ escapeHtml:false });\n");
				printer.Print("		  text = text + result;\n");
				printer.Print("		  dwr.util.setValue(\"resultdiv\", text,{ escapeHtml:false });\n");

				printer.Print("	}\n");
				//	printer.Print("}\n");
			}

			PrintMessage(printer, message ,strResponse,file);

			printer.Print("</script>\n");

			printer.Print("<style>\n");
			printer.Print(" ul {\n");
			printer.Print("     font: normal 12px Arial;\n");
			printer.Print("     list-style-type: none;\n");
			printer.Print("    }\n\n");
			printer.Print("span.label {\n");
			printer.Print("    padding-left: 0px;\n");
			printer.Print("    padding-bottom: 5px;\n");
			printer.Print("    font: normal 12px Arial;\n");
			printer.Print("    float: left;\n");
			printer.Print("    width: 100px;\n");
			printer.Print("    border: solid 0px #6f879e;\n");
			printer.Print("    }\n\n");
			printer.Print("\tspan.leftitem {\n");
			printer.Print("    padding-left: 1px;\n");
			printer.Print("    padding-right: 1px;\n");
			printer.Print("    border: solid 0px #6f879e;\n");
			printer.Print("    }\n\n");
			printer.Print("</style>\n\n");
			printer.Print("</head>\n\n");
			printer.Print("<body>\n\n");
			printer.Indent();
			printer.Print("<form action=\"#\" method=\"post\">","name",file_name,"MsgName",UnqualifiedClassOrEnumOrFieldName(message));
			printer.Indent();  

			printer.Print("\n\n<fieldset>");
			printer.Print("\n\t<legend>`MsgName`:</legend>\n\n\t","MsgName",UnderscoresToCapitalizedCamelCase(UnqualifiedClassOrEnumOrFieldName(message)));
			std::string prefix = std::string ("") + CamelCaseToLower(UnqualifiedClassOrEnumOrFieldName(message));
			printer.Indent();

			//PRINT DATA OF <BODY> TAG
			PrintJspBodyData(printer,message,prefix,file);

			printer.Print("\n\n</fieldset>");
			printer.Outdent();

			printer.Print("\n<input type=\"button\" value=\"Submit\" onclick=\"get`filename`Dto()\">\n\n","filename",UnqualifiedClassOrEnumOrFieldName(message));
			printer.Outdent();   
			printer.Print("</form>\n");
			printer.Print("<div id=\"resultdiv\"></div>\n");
			printer.Outdent();
			printer.Print("</body>\n");  
			printer.Print("</html>");
		}
	}
}


void RevAjaxDwrJspCodeGen::PrintJspBodyData(io::Printer &printer, const Descriptor & message ,const std::string &prefix,const FileDescriptor & file) const
{
	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		const FieldDescriptor &field ( *message.field(i) );
		std::string strFieldHide=field.options().GetExtension(FluxFldHide);
		myfieldlist.push_back(VariableName(field));
		map<std::string, std::string> variables;
		variables["name"]             = VariableName(field);
		variables["prefix"]           = prefix;
		variables["var_name"]	      = VariableName(field);
		variables["test_value"] 	  = TestValueAsString(field,true,true);
		//Override test_value if FluxFldTestVal option is set
		std::string strFluxFldTestVal=field.options().GetExtension(FluxFldTestVal);
		if(0 != strFluxFldTestVal.length())
		{
			variables["test_value"] = strFluxFldTestVal;
		}
		std::string strFluxMsgHbmKey=field.options().GetExtension(FluxFldPk);
		if(0 != strFluxMsgHbmKey.length())
		{
			variables["test_value"] = "";//No default value for primary keys..
		}
		else if(XmlDataType(field)=="String")//We do not want this logic to kick in if field had FluxFldPk option set
		{ 
			std::string temp=variables["test_value"]; 
			size_t pos=temp.find_last_of("\"");
			variables["test_value"]=temp.substr(1,pos-1);
		}

		char a=0;    
		int counter=0;
		for (list<std::string>::iterator it=myfieldlist.begin();it!=myfieldlist.end();++it)
		{
			if(*it==VariableName(field)) 
			{
				counter+=1;
			}
		}

		if(counter>1)
		{
			a=63+counter;
			std::string s(&a,1);
			variables["var_name"]=VariableName(field)+s;	
			//printer.Print(variables,"#####`var_name`\n") ;
		}

		switch (field.type()) 
		{
			case FieldDescriptor::TYPE_MESSAGE:
			case FieldDescriptor::TYPE_GROUP:
				variables["type"] = QualifiedJavaClassOrEnumName(*field.message_type()) + " ";
				isComplex = true;
				break;
			default:variables["type"] = "";
		}
		if (field.is_repeated()) 
		{     
			printer.Indent();
			if(isComplex)
			{
				const Descriptor &newmessage(*field.message_type());
				printer.Print("\n\n<fieldset>");
				printer.Print("\n\t<legend>`MsgName`:</legend>\n\n\t","MsgName",UnderscoresToCapitalizedCamelCase(field));
				std::string childPrefix = prefix +"."+VariableGetterName(field) + "()";
				PrintJspBodyData(printer,newmessage,childPrefix,file);
				printer.Print("\n\n</fieldset>");
			}
			else
			{
				printer.Print("<span class=\"label\" >`id`</span>","id",UnderscoresToCapitalizedCamelCase(field));
				printer.Print("\n<span class=\"leftitem\">");
				if(strFieldHide.length()==0)
				{
					for(int i=0;i<4;i++)
					{
						printer.Print("\n\t\t<input type=\"checkbox\" name=");
						printer.Print(variables,"\"`var_name`\" id=\"`var_name`\" value=\"`test_value`\">`test_value`");
					}
					printer.Print("\n</span><br/><br/>");
				}
			}
			printer.Outdent();       
		}
		else 
		{  
			if(isComplex)
			{           
				const Descriptor &newmessage(*field.message_type());
				printer.Print("\n\n<fieldset>");
				printer.Print("\n\t<legend>`MsgName`:</legend>\n\n\t","MsgName",UnderscoresToCapitalizedCamelCase(field));
				std::string childPrefix = prefix +"."+VariableGetterName(field) + "()";
				PrintJspBodyData(printer,newmessage,childPrefix,file);
				printer.Print("\n\n</fieldset>");
			}
			else if(XmlDataType(field)=="Enumeration")
			{
				if(strFieldHide.length()==0)
				{
					const EnumDescriptor &enum1 (*field.enum_type()) ;
					printer.Print("\n<span class=\"label\" >`FieldName`</span>","FieldName",UnderscoresToCapitalizedCamelCase(field)); 
					printer.Print("<span class=\"leftitem\">");
					printer.Print(variables,"\n	<select name=\"`var_name`\" id=\"`var_name`\">\n");

					for (int k = 0; k < enum1.value_count(); ++k) 
					{
						const EnumValueDescriptor &ev (*enum1.value(k));
						printer.Print("			<option value=\"`enum_name`\">`enum_name`</option>\n","enum_name",ev.name());
					}
					printer.Print("	</select>\n");
					printer.Print("</span><br/><br/>\n");
					printer.Print("\n");
				}
			}
			else
			{            
				if(strFieldHide.length()==0)
				{
					printer.Print("\n<span class=\"label\" >`FieldName`</span>","FieldName",UnderscoresToCapitalizedCamelCase(field));
					printer.Print(variables,"\n<span class=\"leftitem\"><input type=\"text\" name=\"`var_name`\" id=\"`var_name`\" value=\"`test_value`\"></span><br/><br/>");
					printer.Print("\n");
				}
			}
		}
   }
}

bool RevAjaxDwrJspCodeGen::Generate(const FileDescriptor* file,
                                    const std::string& parameter,
                                    OutputDirectory* output_directory,
                                    std::string* error) const 
{

                  std::string cpp_filename ( file->name());
                  size_t pos = cpp_filename.find_first_of ('.');
                  std::string file_name = cpp_filename.substr(0,pos);
                  PrintMessages  (*file,*output_directory);
                  return true;

}
int main(int argc, char* argv[]) 
   {
        if(getenv("DEBUG_ENABLE"))
                sleep(30);
	RevAjaxDwrJspCodeGen generator;
	return PluginMain(argc, argv, &generator);
   }
