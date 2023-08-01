/**
 * Protocol Buffer CPP Test Code Generator Plugin for protoc
 * By Dev-1
 *
 */

#include<list>
#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#define TEST_VALUE "4"

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class RevAjaxInterfaceImplCodeGen : public FluxCodeGenerator {
        protected:
            void PrintMessage(io::Printer &printer, const FileDescriptor & file,const Descriptor & message,std::string &file_name) const ;
            void PrintMessages(io::Printer &printer, const FileDescriptor & file) const ;
            void PrintSetterInitial(io::Printer &printer, const Descriptor & message) const;
            void PrintSetterMethodMain(io::Printer &printer, const Descriptor & message,bool repeatedOrComplex,std::string prefix) const;
            void MethodDeffinition(io::Printer &printer, const FileDescriptor & file,const Descriptor & message) const;
            std::string VariableGetterName(const FieldDescriptor & field) const;
            std::string VariableSetterName(const FieldDescriptor & field) const;
        public:
            mutable list<std::string> mylist;
            int RenameFieldObject(const std::string &object)const;

            RevAjaxInterfaceImplCodeGen(){}
            ~RevAjaxInterfaceImplCodeGen(){}

            bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

std::string RevAjaxInterfaceImplCodeGen::VariableGetterName(const FieldDescriptor & field) const {
        return (std::string("get") + UnderscoresToCapitalizedCamelCase(field));
}

std::string RevAjaxInterfaceImplCodeGen::VariableSetterName(const FieldDescriptor & field) const {
        return (std::string("set") + UnderscoresToCapitalizedCamelCase(field));
}

int RevAjaxInterfaceImplCodeGen::RenameFieldObject(const std::string &object)const
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

void  RevAjaxInterfaceImplCodeGen::PrintSetterMethodMain(io::Printer &printer, const Descriptor & message,bool repeatedOrComplex,std::string prefix) const
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
                        const FieldDescriptor &field (*message.field(i));
                        std::string variable_name=VariableName(field);
                        mylist.push_back(variable_name);
                        map<std::string, std::string> variables;
                        variables["name"]                 = VariableName(field);
                        variables["prefix"]               = prefix;
                        variables["actual_name"]          = UnderscoresToCamelCase(field);
                        variables["camel_actual_name"]    = UnderscoresToCapitalizedCamelCase(field);
                        variables["comment"]              = field.DebugString();
                        variables["getter_name"]          = VariableGetterName(field);
                        variables["setter_name"]          = VariableSetterName(field);
                        variables["DummyVal"]	          = TestValueAsString(field);
                        variables["camel_class_name"]     = UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
                        variables["class_name"]	          = UnqualifiedClassOrEnumOrFieldName(message);
                         variables["dataType"]			  = JavaDataType(field);
                        variables["counterVar"]	          = counterVar;
                        variables["testvalue"]            = TEST_VALUE;
                        variables["child_class_name"]     = "";
                        variables["camel_childclass_name"]= "";
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
                                         variables["type"] = ClassName(*field.message_type());
                                         isComplex = true;
                                         break;
                                 default:
                                         variables["type"] = "";
                         }

                     if (field.is_repeated()) 
                     {
                         
                           printer.Indent();
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
                              variables["child_class_name"]= UnqualifiedClassOrEnumOrFieldName(newmessage);
                              //variables["qualified_child_class"]=ClassName(newmessage);
                              variables["camel_childclass_name"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
                              size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
                              std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
                             // variables["qualified_class_name"]=actual_name;
                              variables["qualified_child_class"]=actual_name;
                              printer.Print(variables,"\n//`comment`\n");
                              printer.Print(variables,"List<`qualified_child_class`.dto.`child_class_name`Dto > `name``obj_suffix`= new ArrayList<`qualified_child_class`.dto.`child_class_name`Dto >();;\n");
                              printer.Print(variables,"\nfor (int `counterVar`=0; `counterVar`<`testvalue` ;++`counterVar`)");
                              printer.Print(variables,"\n{\n");
                              printer.Print(variables,"`qualified_child_class`.dto.`child_class_name`Dto  `name``obj_suffix`dto = new `qualified_child_class`.dto.`child_class_name`Dto();\n");
                              std::string childPrefix =VariableName(field)+variables["obj_suffix"];
                              PrintSetterMethodMain(printer,*field.message_type(),true,childPrefix);
                              printer.Print(variables,"\n`name``obj_suffix`.add");
                              printer.Print(variables,"(`name``obj_suffix`dto);\n");
                               printer.Print(variables,"\n}\n");
                               printer.Print(variables,"`prefix`dto.`setter_name`(`name``obj_suffix`);\n");
                           }
                           else
                           {
                              
                              printer.Print(variables,"List<`dataType`> `name` = new ArrayList<`dataType`>();\n");
                              printer.Print(variables,"for(int `counterVar` =0 ;`counterVar`<4;`counterVar`++)\n{\n");
                              printer.Print(variables,"`name`.add(`DummyVal`);");
                              printer.Print("\n}\n");
                              printer.Print(variables,"`prefix`dto.`setter_name`(`name`);\n");
                           }
                           printer.Outdent();
                          
                          
                     } 
                     else 
                     {
                           if(isComplex)
                              {   
                                 std::string object=VariableName(field);
                                 int obj_count=RenameFieldObject(object);
                                 variables["obj_suffix"]="";
                                 if(obj_count>1)
                                 {
                                    char a=64+obj_count;
                                    variables["obj_suffix"] = a;
                                 }
                                 const Descriptor &complexmessage(*field.message_type());
                                 variables["complexclass_name"]= UnqualifiedClassOrEnumOrFieldName(complexmessage);
                                 size_t pl=QualifiedJavaClassOrEnumName(complexmessage).find_last_of('.');
                                 std::string actual_name=QualifiedJavaClassOrEnumName(complexmessage).substr(0,pl);
                                 variables["qualified_complex"]=actual_name;
                                 printer.Print(variables,"`qualified_complex`.dto.`complexclass_name`Dto `name``obj_suffix`dto =new `qualified_complex`.dto.`complexclass_name`Dto();\n");
                                 std::string childPrefix = VariableName(field)+variables["obj_suffix"];
                                 PrintSetterMethodMain(printer,complexmessage,true,childPrefix);
                                 printer.Print(variables,"`prefix`dto.`setter_name`(`name``obj_suffix`dto);\n");
                              }
                              
                           else 
                           
                           if(!repeatedOrComplex)
                                 {
                                    
                                 }
                                 else
                                 {
                                             printer.Print(variables,"`prefix`dto.`setter_name`"); 
                                             printer.Print(variables,"(`DummyVal`);\n"); 
                                      
                                 }
                      }

                  }
   }


void RevAjaxInterfaceImplCodeGen::PrintSetterInitial(io::Printer &printer, const Descriptor & message) const
{
  
         printer.Indent();
         for (int i = 0; i < message.field_count(); ++i) 
         {
                 
               const FieldDescriptor &field ( *message.field(i) );
               map<std::string, std::string> variables;
               variables["DummyVal"]	           = TestValueAsString(field);
               variables["camel_class_name"]     = UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
               variables["setter_name"]          = VariableSetterName(field);
               if(field.is_repeated()||field.type() == FieldDescriptor::TYPE_GROUP||field.type() == FieldDescriptor::TYPE_MESSAGE)
               {
               }
               else
               {
                     printer.Print(variables,"`camel_class_name`dto.`setter_name`"); 
                     printer.Print(variables,"(`DummyVal`);\n");
               }
         }
         PrintSetterMethodMain(printer,message,false,UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message)));
         printer.Outdent();
}


void RevAjaxInterfaceImplCodeGen::PrintMessage(io::Printer &printer, const FileDescriptor & file,const Descriptor & message,std::string &file_name) const
{
	map<std::string,std::string> variables;
	variables["file_name"]=file_name;
	variables["object_name"]=UnderscoresToCamelCase(file_name);
	//std::string strResponse = message.options().GetExtension(FluxMsgRsp);
	size_t p=QualifiedJavaClassOrEnumName(message).find_last_of('.');
	std::string actual_name=QualifiedJavaClassOrEnumName(message).substr(0,p);
	variables["ClassName"]=actual_name;
	variables["ReqsUnqualifiedClassOrEnumOrFieldName"]=UnqualifiedClassOrEnumOrFieldName(message);
	variables["qualifiedclassname"]=QualifiedJavaClassOrEnumName(message);
	variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
	std::string strResponse=ResponseNameCheckerAndGenerator(message);
	if(0 != strResponse.length())
	{
		variables["strResponse"]=strResponse;
		variables["response"]=UnderscoresToCamelCase(strResponse);
		std::string prefix = std::string ("") +variables["className"];
		for (int i = 0; i < file.message_type_count(); ++i)
		{
			const Descriptor & newmessage(*file.message_type(i));
			if(UnqualifiedClassOrEnumOrFieldName(newmessage)==variables["strResponse"])
			{
				variables["UnqualifiedClassOrEnumOrFieldName"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
				variables["class_name"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
				size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
				std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
				variables["qualified_class_name"]=actual_name;
				variables["pojo_package_name"]=actual_name;
				printer.Print(variables,"public  `pojo_package_name`.dto.`UnqualifiedClassOrEnumOrFieldName`Dto  `className`Dto(`ClassName`.dto.`ReqsUnqualifiedClassOrEnumOrFieldName`Dto `className`Dto)\n{ \n");
				printer.Print(variables,"`qualifiedclassname` `className` = `className`Dto.createProtoBufObj();\n");
				printer.Print(variables,"testHelper.print`ReqsUnqualifiedClassOrEnumOrFieldName`(`className`);\n");
				// printer.Print(variables,"`pojo_package_name`.dto.`UnqualifiedClassOrEnumOrFieldName`Dto `class_name`dto = new `pojo_package_name`.dto.`UnqualifiedClassOrEnumOrFieldName`Dto();\n");
				//PrintSetterInitial(printer,newmessage);
				/*------------------------------------------------------------------------------*/

				/*-------------------------------------------------------------------------------*/
				//printer.Print();
				mylist.clear();
				std::string strNotify = message.options().GetExtension(FluxMsgNotify);
				if(0 != strNotify.length()&& strNotify !="!")
				{
					printer.Print("`package`.dwr.reverseajax.`name`AlertSender alert = new `package`.dwr.reverseajax.`name`AlertSender","package",PackageNameUptoFirstDot(message),"name",UnqualifiedClassOrEnumOrFieldName(message));
					printer.Print(variables,"(`class_name`dto);\n");
					printer.Print("alert.sendAlert();\n");
				}
				printer.Print(variables,"return `object_name`Dao.`className`(`className`Dto);\n");
				// printer.Print(variables,"return `class_name`dto;\n");
				printer.Print("\n}\n");
			}
		}
	}
}


void RevAjaxInterfaceImplCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
{
         //find filename
         std::string cpp_filename ( file.name());
         size_t slashposition=cpp_filename.find_last_of ('/');
         size_t pos1 = cpp_filename.find_first_of ('.');
         std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
         size_t pos = sbstring.find_first_of ('.');
         std::string file_name=sbstring.substr(0,pos);
         //find package name for generated class
         std::string package=file.package();
         size_t p = package.find_last_of('.');
         //find package name for the java file generated
         std::string name = package.substr(0,p);
         printer.Print("package `name`.services.impl;\n","name",name);
         printer.Print("import `name`.services.*;\n","name",name);
         printer.Print("import `name`.dataprintorpopulate.*;\n","name",name);
         printer.Print("import `name`.dao.*;\n","name",name);
         
         map<std::string,std::string> variables;
         variables["name"]=name;
         variables["ClassName"]=package;
         const Descriptor & message(*file.message_type(0));
         variables["firstdot"]=PackageNameUptoFirstDot(message);
         printer.Print("");
         printer.Print("import java.util.*;\n");
         //check reverse ajax is enable or not
         bool notifyAnnotation=isReverseAjaxEnable(file);
         if(notifyAnnotation)
         {
            printer.Print(variables,"import static `firstdot`.dwr.reverseajax.AttributeScriptSessionFilter.SCRIPT_SESSION_ATTR;\n");
            printer.Print("import org.directwebremoting.ScriptSession;\n");
            printer.Print("import org.directwebremoting.WebContextFactory;\n");
            printer.Print(variables,"import `firstdot`.dwr.reverseajax.*;\n");
         }
         printer.Print("public class `file_name`TestImpl implements I`file_name`\n{\n","file_name",file_name);
         printer.Indent();
         printer.Print("`file_name`DataPrintOrPopulate testHelper = new `file_name`DataPrintOrPopulate();\n","file_name",file_name);
         printer.Print("private I`name`Dao `object`Dao;\n","name",file_name,"object",UnderscoresToCamelCase(file_name));
         /*-----------------------------------------------------------------------------------*/
         printer.Print("public I`file_name`Dao get`file_name`Dao() \n{\n","file_name",file_name);
         printer.Print("return `name`Dao;\n","name",UnderscoresToCamelCase(file_name));
         printer.Print("}\n");
         printer.Print("public void set`file_name`Dao(I`file_name`Dao `object`Dao) \n{\n","file_name",file_name,"object",UnderscoresToCamelCase(file_name));
         printer.Print("this.`name`Dao = `name`Dao;\n","name",UnderscoresToCamelCase(file_name));
         printer.Print("\n}\n");
         /*-------------------------------------------------------------------------------------*/
         
         for (int i = 0; i < file.message_type_count(); ++i)
            {
               PrintMessage(printer,file,*file.message_type(i),file_name);
            }
            if(notifyAnnotation)
            {
               printer.Print("public void subscribeAlertService()\n");
               printer.Print("{\n");
               printer.Indent();
               printer.Print("  ScriptSession scriptSession = WebContextFactory.get().getScriptSession();\n");
               printer.Print("  scriptSession.setAttribute(SCRIPT_SESSION_ATTR, true);\n");
               printer.Outdent();
               printer.Print("}\n");
               printer.Print("public void unSubscribeAlertService()\n");
               printer.Print(" {\n");
               printer.Indent();
               printer.Print("ScriptSession scriptSession = WebContextFactory.get().getScriptSession();\n");
               printer.Print("scriptSession.removeAttribute(SCRIPT_SESSION_ATTR);\n");
               printer.Outdent();
               printer.Print("}\n");

         }
            
         printer.Outdent();
         printer.Print("\n}\n");
}

bool RevAjaxInterfaceImplCodeGen::Generate(const FileDescriptor* file,
                                const std::string& parameter,
                                OutputDirectory* output_directory,
                                std::string* error) const 
{
	scoped_ptr<io::ZeroCopyOutputStream> output(
	output_directory->Open(GetPackageDirectoryName(file) + "/services/impl/" + GetFileNameFromFileDescriptor(file) + "TestImpl.java")
	);

	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}


int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	RevAjaxInterfaceImplCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
