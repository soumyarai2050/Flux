/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-1
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include<list>
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class RevAjaxAlertSenderCodeGen: public FluxCodeGenerator 
{
	protected:
		void PrintMessage(io::Printer &printer,const FileDescriptor & file, const Descriptor & message) const;
		void PrintMessages(const FileDescriptor & file,OutputDirectory& output_directory) const;
		std::string VariableGetterName(const FieldDescriptor & field) const;
		void PrintRunMethod(io::Printer &printer, const Descriptor & message,const std::string &prefix) const;

	public:
		mutable list<std::string> mylist;
		int RenameFieldObject(const std::string &object)const;
		RevAjaxAlertSenderCodeGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

std::string RevAjaxAlertSenderCodeGen::VariableGetterName(const FieldDescriptor & field) const {
	return (std::string("get") + UnderscoresToCapitalizedCamelCase(field));
}

int RevAjaxAlertSenderCodeGen::RenameFieldObject(const std::string &object)const
{
    
    std::string obj_name=object;
    list<std::string>::const_iterator it;
      int obj_count=0;
   for (it=mylist.begin(); it!=mylist.end(); ++it)
     {      if(obj_name==(*it))
                  obj_count+=1;
      
     }

    return obj_count;
    
} 

void RevAjaxAlertSenderCodeGen::PrintRunMethod(io::Printer &printer, const Descriptor & message ,const std::string &prefix) const
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
                
               mylist.push_back(VariableName(field));
		variables["name"]             = VariableName(field);
		variables["capitalized_name"] = UnderscoresToCapitalizedCamelCase(field);
		variables["actual_name"]      = UnderscoresToCamelCase(field);
		variables["default"]          = DefaultValueAsString(field);
		variables["comment"]          = field.DebugString();
		variables["getter_name"]      = VariableGetterName(field);
                variables["prefix"]           = prefix;
		variables["DummyVal"]	      = TestValueAsString(field);
		variables["counterVar"]	      = counterVar;
                variables["datatype"]         = JavaDataType(field);
               
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
			isComplex = true;
			break;
			default:variables["type"] = "";
		}


                if (field.is_repeated()) 
		{     
                       
                      
                        if(isComplex)
                        {
                                    std::string object=VariableName(field);
                                    int obj_count=RenameFieldObject(object);
                                    variables["obj_suffix"]="";
                                    if(obj_count>1){
                                    char a=64+obj_count;
                                    variables["obj_suffix"] = a;
                                    }
                                    const Descriptor &newmessage(*field.message_type());
                                    variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
                                    variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
                                    size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
                                    std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
                                    variables["qualified_childclass_name"]=actual_name;
                                    printer.Print(variables,"\nList<`qualified_childclass_name`.dto.`Childmessage`Dto> `name``obj_suffix`dto=`prefix`.`getter_name`();\n");
                                    printer.Print(variables,"\nfor(`qualified_childclass_name`.dto.`Childmessage`Dto  `className``obj_suffix`Dto : `name``obj_suffix`dto)\n");
                                    printer.Print(variables,"{\n");
                                    printer.Indent();
                                    std::string childPrefix = variables["className"]+ variables["obj_suffix"]+"Dto";
                                    PrintRunMethod(printer,*field.message_type(),childPrefix);
                                    printer.Outdent();
                                    printer.Print("\n}\n");
                        }
                        else
                        {
                                    printer.Print(variables,"\nList<`datatype`> `name` =`prefix`.`getter_name`();\n");
                                    printer.Print(variables,"\nfor (`datatype` str`name` :`name`");
                                    printer.Print(variables,")\n{\n");
                                    printer.Indent();
                                    printer.Print(variables,"result = result + \" ReverseAjax =\"+str`name`+\"</br>\";\n");
                                    printer.Outdent();
                                    printer.Print("\n}\n");
                         
                        }
                                     
                      
                      
                }
                else 
		{  
			if(isComplex)
			{
                                    std::string object=VariableName(field);
                                    int obj_count=RenameFieldObject(object);
                                    variables["obj_suffix"]="";
                                    if(obj_count>1){
                                    char a=64+obj_count;
                                    variables["obj_suffix"] = a;
                                    }
                                    const Descriptor &newmessage(*field.message_type());
                                    variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
                                    variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
                                    size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
                                    std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
                                    variables["qualified_childclass_name"]=actual_name;
                                    printer.Print(variables,"\n`qualified_childclass_name`.dto.`Childmessage`Dto `name``obj_suffix`dto=`prefix`.`getter_name`();\n");
                                    std::string childPrefix = variables["name"]+ variables["obj_suffix"]+"dto";
                                    PrintRunMethod(printer,*field.message_type(),childPrefix);
                                  
			}
			else
			{
                                    printer.Print(variables,"result = result + \" ReverseAjax `name` = \" +`prefix`.`getter_name`() +\"</br>\";\n");
			}
		}

	}
              
}


void RevAjaxAlertSenderCodeGen::PrintMessage(io::Printer &printer,const FileDescriptor & file, const Descriptor & message) const 
{
              
               //std::string strNotify = message.options().GetExtension(FluxMsgNotify);
               map<std::string,std::string> variables;
               variables["requestname"]=UnqualifiedClassOrEnumOrFieldName(message);
               std::string strResponse=ResponseNameCheckerAndGenerator(message);
               for (int i = 0; i < file.message_type_count(); ++i) 
                  {
                        const Descriptor & newmessage(*file.message_type(i));
                        if(UnqualifiedClassOrEnumOrFieldName(newmessage)==strResponse)
                           { 
                              variables["UnqualifiedClassOrEnumOrFieldName"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
                              size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
                              std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
                              variables["qualified_class_name"]=actual_name;
                              variables["class_name"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
                              printer.Print(variables,"private `qualified_class_name`.dto.`UnqualifiedClassOrEnumOrFieldName`Dto `class_name`Dto;\n");
                              printer.Print(variables,"public `requestname`AlertSender(`qualified_class_name`.dto.`UnqualifiedClassOrEnumOrFieldName`Dto `class_name`Dto) \n{\n");
                              printer.Indent();
                              printer.Print(variables,"this.`class_name`Dto = `class_name`Dto;\n");
                              printer.Outdent();
                              printer.Print(variables,"}\n");
                              printer.Print("public void run() {\n");
                              printer.Indent();
                              printer.Print("updatePage();\n");
                              printer.Outdent();
                              printer.Print("\n}\n");
                              printer.Print(variables,"private void updatePage()\n");
                              printer.Print("{\n");
                              printer.Indent();
                              printer.Print(variables,"String page = ServerContextFactory.get().getContextPath() + \"/jsp/`requestname`ReverseAjax.jsp\";\n");
                              printer.Print("ScriptSessionFilter attributeFilter = new AttributeScriptSessionFilter(SCRIPT_SESSION_ATTR);\n");
                              printer.Print("Browser.withPageFiltered(page, attributeFilter, new Runnable()\n");
                              printer.Print("{\n");
                              printer.Print("@Override\n");
                              std::string prefix = std::string ("") +UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage))+"Dto";
                              printer.Indent();
                              printer.Print("public void run()\n{\n");
                              printer.Indent();
                              printer.Print("String result = \"***************Result From Revere Ajax**************<br/>\";\n");
                              PrintRunMethod(printer,newmessage,prefix);
                              //mylist.clear();
                              printer.Print("ScriptSessions.addFunctionCall(\"reverseAjacResult\",result);\n");
                              printer.Outdent();
                              printer.Print("  }\n");
                              printer.Outdent();
                              printer.Print(" });");
                              printer.Outdent();
                              printer.Print("\n}\n");
                        
                     }   
               }

}


void RevAjaxAlertSenderCodeGen::PrintMessages(const FileDescriptor & file,OutputDirectory& output_directory) const
{      
            
            //bool notifyAnnotation=false;
            for(int i = 0; i < file.message_type_count(); ++i)
            {
               const Descriptor & message(*file.message_type(i));
               map<std::string,std::string> variables;
               variables["UnqualifiedClassOrEnumOrFieldName"]=UnqualifiedClassOrEnumOrFieldName(message);
               std::string  strResponse=message.options().GetExtension(FluxMsgRsp);
               std::string strNotify = message.options().GetExtension(FluxMsgNotify);
               std::string first_dot_pos=PackageNameUptoFirstDot(message);
               size_t pl=QualifiedJavaClassOrEnumName(message).find_last_of('.');
               std::string actual_name=first_dot_pos.substr(0,pl);
              // std::string rps=ResponseNameCheckerAndGenerator(message);
               bool notifyAnnotation=isReverseAjaxEnable(file); 
            if(notifyAnnotation)
            {
                     std::string output_filename =actual_name+"/dwr/reverseajax/"+UnqualifiedClassOrEnumOrFieldName(message)+"AlertSender.java";
                     scoped_ptr<io::ZeroCopyOutputStream> output(output_directory.Open(output_filename));
                     io::Printer printer(output.get(), '`');
                     printer.Print("package com.dwr.reverseajax;\n");
                     printer.Print("import static com.dwr.reverseajax.AttributeScriptSessionFilter.SCRIPT_SESSION_ATTR;\n");
                     printer.Print("import java.util.concurrent.ScheduledThreadPoolExecutor;\n");
                     printer.Print("import java.util.concurrent.TimeUnit;\n");
                     printer.Print("import org.directwebremoting.Browser;\n");
                     printer.Print("import org.directwebremoting.ScriptSessionFilter;\n");
                     printer.Print("import org.directwebremoting.ScriptSessions;\n");
                     printer.Print("import org.directwebremoting.ServerContextFactory;\n");
                     printer.Print("import org.directwebremoting.impl.DaemonThreadFactory;\n");
                     printer.Print("import java.util.*;\n");
                     printer.Print("public class `name`AlertSender implements Runnable {\n","name",UnqualifiedClassOrEnumOrFieldName(message));
                     printer.Indent();
                     printer.Print(" public void sendAlert()\n");
                     printer.Print("    {\n");
                     printer.Indent();
                     printer.Print("  ScheduledThreadPoolExecutor executor = new ScheduledThreadPoolExecutor(1, new DaemonThreadFactory());\n");
                     printer.Print("  executor.schedule(this, 20, TimeUnit.SECONDS);\n");
                     printer.Outdent();
                     printer.Print(" }\n");
                     printer.Indent();
                     PrintMessage(printer,file,*file.message_type(i));
                     printer.Outdent();
                     printer.Outdent();
                     printer.Print("\n}\n");
                  }
            }
           
        
}


bool RevAjaxAlertSenderCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {
                                 PrintMessages  (*file,*output_directory);
                                 return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	RevAjaxAlertSenderCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
