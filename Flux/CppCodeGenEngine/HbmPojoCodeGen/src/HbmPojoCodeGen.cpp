/**
 * Protocol Buffer CPP Test Code Generator Plugin for protoc
 * By Dev-2
 *
 */
#include<list>
#include<set>
#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <boost/serialization/set.hpp>
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class HbmPojoCodeGen : public FluxCodeGenerator 
{
	protected:
	    void        PrintMessageDto(io::Printer &printer, const FileDescriptor & file,const Descriptor & message) const ;
	    void        PrintAllDto(const FileDescriptor & file,OutputDirectory& output_directory) const;
	    void        PrintDtoBodyMethod(io::Printer &printer,const Descriptor & message) const;
	    void        CreateProtoBufObjMethod(io::Printer &printer,const Descriptor & message) const ;
	    void 	PrintRepNormalFieldDto(io::Printer &printer, const FileDescriptor & file,const Descriptor & message,const FieldDescriptor &field) const;
	    void        PrintParseFromMethodBody(io::Printer &printer,const Descriptor & message) const;
	    std::string      VariableGetterName(const FieldDescriptor & field) const;
	    std::string      VariableSetterName(const FieldDescriptor & field) const;
	public:
	    mutable list<std::string> mylist;
	    mutable std::map<std::string, std::set<std::string>* > im;
	    int RenameFieldObject(const std::string &object)const;

	    HbmPojoCodeGen(){}
	    ~HbmPojoCodeGen(){} 

	    bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};


std::string HbmPojoCodeGen::VariableGetterName(const FieldDescriptor & field) const 
{
	return (std::string("get") + UnderscoresToCapitalizedCamelCase(field));
}

std::string HbmPojoCodeGen::VariableSetterName(const FieldDescriptor & field) const 
{
	return (std::string("set") + UnderscoresToCapitalizedCamelCase(field));
}

void HbmPojoCodeGen::CreateProtoBufObjMethod(io::Printer &printer,const Descriptor & message) const 
{
	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		map<std::string,std::string> variables;
		const FieldDescriptor &field (*message.field(i) );
		variables["name"]= VariableName(field);
		variables["Name"]= UnderscoresToCapitalizedCamelCase(field);
		variables["getter_name"]          = VariableGetterName(field);
		variables["setter_name"]          = VariableSetterName(field);
		variables["parent_message_name"]=UnqualifiedClassOrEnumOrFieldName(message);
		variables["parent_message"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
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
			if(isComplex)
			{
				const Descriptor &newmessage(*field.message_type());
				variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
				variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
				size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
				std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
				variables["qualified_childclass_name"]=actual_name;
				printer.Print(variables,"if (null != this.`name`) {");
				printer.Print(variables,"\nfor(`qualified_childclass_name`.dto.`Childmessage`Dto `className`dto : this.`name`)\n");
				printer.Indent();
				printer.Print("{\n");
				printer.Indent();
				printer.Print(variables,"this.`parent_message`Builder.add`Name`(`className`dto.createProtoBufObj());\n");
				printer.Outdent();
				printer.Print("}\n");
				printer.Outdent();
				printer.Print("}\n");
			}
		}
		else
		{
			if(isComplex)
			{
				const Descriptor &newmessage(*field.message_type());
				variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
				variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
				//printer.Indent();
				printer.Print(variables,"if (null != `name`) {\n");
				printer.Print(variables,"this.`parent_message`Builder.`setter_name`(`name`.createProtoBufObj());\n");
				printer.Print("}\n");
				//printer.Outdent();
			}
		}
	} 
}


void HbmPojoCodeGen::PrintDtoBodyMethod(io::Printer &printer,const Descriptor & message) const 
{  
	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		map<std::string,std::string> variables;
		const FieldDescriptor &field (*message.field(i) );
		variables["name"]          = VariableName(field);
		variables["Name"]          = UnderscoresToCapitalizedCamelCase(VariableName(field));
		variables["getter_name"]   = VariableGetterName(field);
		variables["setter_name"]   = VariableSetterName(field);
		variables["builder_name"]  = UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
		variables["dataType"]      = JavaDataType(field);
		variables["DummyVal"]	         = TestValueAsString(field);
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
				variables["type"] = QualifiedJavaClassOrEnumName(*field.message_type());
				isComplex = true;
				break;
			default:
				variables["type"] = "";
		}
		if (field.is_repeated()) 
		{
			if(isComplex)
			{
				const Descriptor &newmessage(*field.message_type());
				variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
				size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
				std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
				variables["qualified_class_name"]=actual_name;
				printer.Print(variables,"\npublic List<`qualified_class_name`.dto.`Childmessage`Dto> `getter_name`() \n{\n");
				printer.Indent();
				printer.Print(variables,"\nreturn this.`name`;\n");
				printer.Outdent();
				printer.Print("}\n\n");
				printer.Print(variables,"public void `setter_name`(List<`qualified_class_name`.dto.`Childmessage`Dto> `name`) \n{\n");
				printer.Indent();
				printer.Print(variables,"this.`name` = `name`;\n");
				printer.Outdent();
				printer.Print("}\n\n");
			}
			else
			{
				size_t pos_last				=	QualifiedJavaClassOrEnumName(message).find_last_of('.');
				variables["package_name"]	=	QualifiedJavaClassOrEnumName(message).substr(0,pos_last);
				variables["full_name"]		=	variables["package_name"]+".dto."+	UnderscoresToCapitalizedCamelCase(VariableName(field))+"Dto";
				printer.Print(variables,"public List<`full_name`> `getter_name`() \n{\n");
				printer.Indent();
				printer.Print(variables,"return `name`;\n");
				printer.Outdent();
				printer.Print("\n}\n");
				printer.Print(variables,"public void `setter_name`(List<`full_name`> `name`) \n{\n");
				//printer.Print(variables,"for (`full_name` id : `name`)\n{\n");
				printer.Print(variables,"\t this.`name` = `name`;\n");
				printer.Print("\n}\n");
			}

		}
		else
		{
			if(isComplex)
			{
				const Descriptor &newmessage(*field.message_type());
				variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);

				variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
				size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
				std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
				variables["qualified_childclass_name"]=actual_name;

				printer.Print(variables,"public `qualified_childclass_name`.dto.`Childmessage`Dto `getter_name`() \n{\n");
				printer.Indent();
				printer.Print(variables,"\nreturn this.`name`;\n");
				printer.Outdent();
				printer.Print(" \n}\n");
				printer.Print(variables,"public void `setter_name`(`qualified_childclass_name`.dto.`Childmessage`Dto `name`) \n{\n");
				printer.Indent();
				printer.Print(variables,"this.`name` = `name`;\n");
				printer.Outdent();
				printer.Print("\n}\n");
			}
			else
			{
				if( variables["dataType"]=="Enumeration")
				{
					variables["enum"]=ClassName(*field.enum_type());
					printer.Print(variables,"public `enum` `getter_name`() \n{\n");
					printer.Indent();
					printer.Print(variables,"return this.`builder_name`Builder.`getter_name`();\n");
					printer.Outdent();
					printer.Print("\n}\n");
					printer.Print(variables,"public void `setter_name`(`enum` `name`) \n{\n");
					printer.Indent();
					printer.Print(variables,"this.`builder_name`Builder.`setter_name`(`name`);\n");
					printer.Outdent();
					printer.Print("\n}\n");
				}
				else
				{
					if(variables["dataType"]!="String")
					{
						printer.Print(variables,"public `dataType` `getter_name`() \n{\n");
						printer.Indent();
						printer.Print(variables,"if(`builder_name`Builder.has`Name`())\n");
						printer.Print(variables,"\t\treturn this.`builder_name`Builder.`getter_name`();\n");
						printer.Print(variables,"else\n\t\treturn null;\n");
						printer.Outdent();
						printer.Print("}\n");
						//setter methods
						printer.Print(variables,"public void `setter_name`(`dataType` `name`) \n{\n");
						printer.Indent();
						printer.Print(variables,"if (`name`!= null)\n");
						printer.Print(variables,"\t\tthis.`builder_name`Builder.`setter_name`(`name`);\n");
						printer.Outdent();
						printer.Print("\n}\n");
					}
					else
					{
						printer.Print(variables,"public `dataType` `getter_name`() \n{\n");
						printer.Indent();
						printer.Print(variables,"return this.`builder_name`Builder.`getter_name`();\n");
						printer.Outdent();
						printer.Print("\n}\n");
						//setter methods
						printer.Print(variables,"public void `setter_name`(`dataType` `name`) \n{\n");
						printer.Indent();
						printer.Print(variables,"this.`builder_name`Builder.`setter_name`(`name`);\n");
						printer.Outdent();
						printer.Print("\n}\n");
					}
				}
			}
		}
	}
}

void HbmPojoCodeGen::PrintParseFromMethodBody(io::Printer &printer,const Descriptor & message) const 
{
	for (int i = 0; i < message.field_count(); ++i)
	{
		bool isComplex = false;
		const FieldDescriptor &field (*message.field(i) );
		map<std::string,std::string> variables;
		variables["name"]= VariableName(field);
		variables["Name"]=UnderscoresToCapitalizedCamelCase(VariableName(field));
		variables["class_name"]=UnqualifiedClassOrEnumOrFieldName(message);
		variables["lower_camel_class_name"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
		variables["getter_name"]   = VariableGetterName(field);
		variables["setter_name"]   = VariableSetterName(field);
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
				variables["type"] = QualifiedJavaClassOrEnumName(*field.message_type());
				isComplex = true;
				break;
			default:
				variables["type"] = "";
		}
		if (field.is_repeated()) 
		{
			if(isComplex)
			{
			const Descriptor &newmessage(*field.message_type());
			variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
			variables["fullyqualified_class_name"]=QualifiedJavaClassOrEnumName(newmessage);
			size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
			std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
			variables["qualified_class_name"]=actual_name;
			printer.Print(variables,"if (null != `lower_camel_class_name`Builder.`getter_name`List() && `lower_camel_class_name`Builder.`getter_name`List().size() > 0)\n");
			printer.Print(variables,"{\n");
			printer.Indent();
			printer.Print(variables,"List<`fullyqualified_class_name`> t`Name` =`lower_camel_class_name`Builder.`getter_name`List();\n");
			//printer.Print(variables,"System.out.println(\"List is= \"+ t`Name`);\n");
			printer.Print(variables,"`name` = new ArrayList<`qualified_class_name`.dto.`Childmessage`Dto>();\n");
			printer.Print(variables,"for (`fullyqualified_class_name` tmp`Childmessage` : t`Name`)\n");
			printer.Print(variables,"{\n");
			printer.Indent();
			printer.Print(variables,"`qualified_class_name`.dto.`Childmessage`Dto tmp`Childmessage`Dto = new `qualified_class_name`.dto.`Childmessage`Dto();\n");
			printer.Print(variables,"tmp`Childmessage`Dto.parseFrom(new ByteArrayInputStream(tmp`Childmessage`.toByteArray()));\n");
			printer.Print(variables,"`name`.add(tmp`Childmessage`Dto);\n");
			printer.Outdent();
			printer.Print(variables,"}\n");
			printer.Outdent();
			printer.Print(variables,"}\n");

			}
			else
			{
				throw "Repeated simple type not supported";
			}
		}
		else
		{
			if(isComplex)
			{
				const Descriptor &newmessage(*field.message_type());
				variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
				variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
				size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
				std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
				variables["qualified_class_name"]=actual_name;
				printer.Print(variables," if (null != `lower_camel_class_name`Builder.`getter_name`()) {\n");
				printer.Indent();
				printer.Print(variables,"`name` = new `qualified_class_name`.dto.`Childmessage`Dto();\n");
				printer.Print(variables,"`name`.parseFrom(new ByteArrayInputStream(`lower_camel_class_name`Builder.`getter_name`().toByteArray()));\n");
				printer.Outdent();
				printer.Print("}\n");
			}//no else required
		}
	}
}
void HbmPojoCodeGen::PrintMessageDto(io::Printer &printer, const FileDescriptor & file,const Descriptor & message) const 
{
	std::string package=file.package();
	size_t pos = package.find_last_of('.');
	std::string name =package.substr(0,pos);
	map<std::string,std::string> variables;
	variables["ClassName"]=file.package();
	variables["UnqualifiedClassOrEnumOrFieldName"]=UnqualifiedClassOrEnumOrFieldName(message);
	size_t pos_last=QualifiedJavaClassOrEnumName(message).find_last_of('.');
	std::string actual_package=QualifiedJavaClassOrEnumName(message).substr(0,pos_last);
	variables["qualified_classname"]=QualifiedJavaClassOrEnumName(message);
	variables["package_name"]=actual_package;
	variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
	printer.Print(variables,"package `package_name`.dto;\n");
	printer.Print("import java.util.List;\n");
	printer.Print("import java.util.ArrayList;\n");
	printer.Print("import java.io.ByteArrayInputStream;\n");
	printer.Print("import java.io.IOException;\n");
	printer.Print(variables,"import `ClassName`.`UnqualifiedClassOrEnumOrFieldName`;\n");
	printer.Print(variables,"public class `UnqualifiedClassOrEnumOrFieldName`Dto\n");
	printer.Print("{\n");
	printer.Indent();
	printer.Print(variables,"`qualified_classname`.Builder `className`Builder = `qualified_classname`.newBuilder();\n");

	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		const FieldDescriptor &field (*message.field(i) );
		variables["name"]= VariableName(field);
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
				variables["type"] = QualifiedJavaClassOrEnumName(*field.message_type());
				isComplex = true;
				break;
			default:
				variables["type"] = "";
		}
		if (field.is_repeated()) 
		{
			if(isComplex)
			{
				const Descriptor &newmessage(*field.message_type());
				variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
				size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
				std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
				variables["qualified_class_name"]=actual_name;
				printer.Print(variables,"private List<`qualified_class_name`.dto.`Childmessage`Dto> `name`;\n");
			}
			else
			{
				variables["full_name"]		=	variables["package_name"]+".dto."+	UnderscoresToCapitalizedCamelCase(VariableName(field))+"Dto";
				printer.Print(variables,"private List<`full_name`> `name`;\n");
			}
		}
		else
		{
			if(isComplex)
			{
				const Descriptor &newmessage(*field.message_type());
				variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
				variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
				size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
				std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
				variables["qualified_class_name"]=actual_name;
				printer.Print(variables,"private `qualified_class_name`.dto.`Childmessage`Dto `name`;\n "); 
			}//else not required
		}
	}

	printer.Print("\npublic `name` createProtoBufObj()\n{\n","name",UnqualifiedClassOrEnumOrFieldName(message));
	printer.Indent();
	CreateProtoBufObjMethod(printer,message);      
	printer.Print("return this.`name`Builder.build();\n","name",UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message)));
	printer.Outdent();
	printer.Print("}\n");

	//Method to create dto object from protobuf object
	printer.Print("\npublic void parseFrom(java.io.InputStream input) \n");
	printer.Print("{\n");
	printer.Print("	  try \n");
	printer.Print("	  {\n");

	printer.Print("         `className`Builder.mergeFrom(input);\n","className",UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message)));
	printer.Indent();
	PrintParseFromMethodBody(printer,message);
	printer.Outdent();
	printer.Print("} \n");
	printer.Print("	catch (IOException e)\n");
	printer.Print("	{\n");
	printer.Print("		e.printStackTrace();\n");
	printer.Print("	}\n");
	printer.Print("}\n\n");


	PrintDtoBodyMethod(printer,message);
	//Below commented call generates getters and setters for Many-to-one realtionship FK, Not needed anymore.
	//PrintFkBodyMethod(printer,message);
	printer.Outdent();
	printer.Print("\n}\n");
}




void HbmPojoCodeGen::PrintRepNormalFieldDto(io::Printer &printer, const FileDescriptor & file,const Descriptor & message,const FieldDescriptor &field) const
{
	map<std::string,std::string>variables;
	variables["class_name"]			=	UnderscoresToCapitalizedCamelCase(VariableName(field));
	variables["class_obj_name"]		=	UnderscoresToCamelCase(field);
	variables["fk_obj_name"]		=	UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message))+"Fk";
	variables["fk_class_name"]		=	UnqualifiedClassOrEnumOrFieldName(message);
	variables["data_type"]			=   JavaDataType(field);
	size_t pos_last					=	QualifiedJavaClassOrEnumName(message).find_last_of('.');
	variables["package_name"]		=	QualifiedJavaClassOrEnumName(message).substr(0,pos_last);
	variables["fk_full_name"]		=	variables["package_name"]+".dto."+UnqualifiedClassOrEnumOrFieldName(message);
	printer.Print(variables,"package `package_name`.dto;\n");
	printer.Print("import java.util.List;\n");
       
	printer.Print(variables,"public class `class_name`Dto\n");
	printer.Print("{\n");
	printer.Indent();
	printer.Print(variables,"private `data_type` `class_obj_name`;\n");
	printer.Print(variables,"private `fk_full_name`Dto `fk_obj_name`;\n\n");
	
	printer.Print(variables,"public `data_type` get`class_name`()\n");
	printer.Print("{\n");
	printer.Print(variables,"	return `class_obj_name`;\n");
	printer.Print("}\n\n");

	printer.Print(variables,"public void set`class_name`(`data_type` `class_obj_name`) \n");
	printer.Print("{\n");
	printer.Print(variables,"	this.`class_obj_name` = `class_obj_name`;\n");
	printer.Print("}\n\n");

	printer.Print(variables,"public `fk_full_name`Dto get`fk_class_name`Fk() \n");
	printer.Print("{\n");
	printer.Print(variables,"	return `fk_obj_name`;\n");
	printer.Print("}\n\n");

	printer.Print(variables,"public void set`fk_class_name`Fk(`fk_full_name`Dto `fk_obj_name`) \n");
	printer.Print("{\n");
	printer.Print(variables,"	this.`fk_obj_name` = `fk_obj_name`;\n");
	printer.Print("}\n");
	printer.Outdent();
	printer.Print("}\n");

	
}


void HbmPojoCodeGen::PrintAllDto(const FileDescriptor & file,OutputDirectory& output_directory) const
{      
	ReadStdMapFromFile(im,"../temp/RepeatedFieldDependencyMapSet.txt");
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor & message(*file.message_type(i));
		std::string output_filename = GetJavaComponentFullPathFileName(message,DTO_COMP_NAME);
		scoped_ptr<io::ZeroCopyOutputStream> output(output_directory.Open(output_filename));
		io::Printer printer(output.get(), '`');
		PrintMessageDto(printer, file,*file.message_type(i));
	}

	//for generating POJO for repeated normal fields

	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor & message(*file.message_type(i));
		//  std::string strResPonse=message.options().GetExtension(FluxMsgRsp);
		for (int i = 0; i < message.field_count(); ++i) 
		{
			const FieldDescriptor &field (*message.field(i) );
			if(field.is_repeated())
			{
				if(field.type() != FieldDescriptor::TYPE_GROUP && field.type() != FieldDescriptor::TYPE_MESSAGE)
				{
					std::string class_name=UnderscoresToCapitalizedCamelCase(field);
					std::string output_filename = GetJavaComponentFullPathFileName(message,DTO_COMP_NAME);
					scoped_ptr<io::ZeroCopyOutputStream> output(output_directory.Open(output_filename));
					io::Printer printer(output.get(), '`');
					PrintRepNormalFieldDto(printer, file,message,field);
				}
			}
		}
	}
}

bool HbmPojoCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	PrintAllDto  (*file,*output_directory);
	return true;  
}

int main(int argc, char* argv[]) {
         if(getenv("DEBUG_ENABLE"))
                sleep(30);
              
 
         HbmPojoCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
