/**
 * Protocol Buffer CPP Test Code Generator Plugin for protoc
 * By Dev-1
 *
 */

#include<list>
#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <boost/serialization/vector.hpp>
#include <boost/serialization/set.hpp>
#include<set>
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class HibernateHbmFileCodeGen : public FluxCodeGenerator {
	protected:
            void        PrintMessage(io::Printer &printer,const Descriptor & message,bool enableBdir,std::string prefix) const ;
            void        PrintMessages(io::Printer &printer, const FileDescriptor & file) const;
            void        PrintComplexMessages(io::Printer &printer,const Descriptor & message) const; 
            void        PrintMapping(io::Printer &printer,const Descriptor & message) const;
            std::string      VariableGetterName(const FieldDescriptor & field) const;
            std::string      VariableSetterName(const FieldDescriptor & field) const;
	public:
            mutable list<std::string> mylist;
            mutable std::map<std::string, std::set<std::string>* > im;
            mutable std::set<std::string> os; 
            int RenameFieldObject(const std::string &object)const;
          
            HibernateHbmFileCodeGen(){}
            ~HibernateHbmFileCodeGen(){} 
            
            bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};


std::string HibernateHbmFileCodeGen::VariableGetterName(const FieldDescriptor & field) const {
	return (std::string("get") + UnderscoresToCapitalizedCamelCase(field));
}

std::string HibernateHbmFileCodeGen::VariableSetterName(const FieldDescriptor & field) const {
	return (std::string("set") + UnderscoresToCapitalizedCamelCase(field));
}

void HibernateHbmFileCodeGen::PrintComplexMessages(io::Printer &printer,const Descriptor & message) const 
{
	map<std::string,std::string>variables;
	std::map<std::string,set<std::string>* >::const_iterator itr;
	std::set<std::string> *ptrFKSet = new std::set<std::string>;
	for( itr = im.begin(); itr != im.end(); ++itr )
	{
		std::string key = itr->first;
		if(UnqualifiedClassOrEnumOrFieldName(message)==key)
		ptrFKSet=itr->second;
	}
	for (set<std::string>::iterator it = ptrFKSet->begin(); it!=ptrFKSet->end(); ++it) 
	{	
		std::string str=*it;
		size_t pos=str.find_last_of('.');	
		variables["full_name"]	=	str.substr(0,pos)+".dto."+str.substr(pos+1,str.size()-1);
		variables["fk_name"]	=	str.substr(pos+1,str.size()-1);
		variables["fk_obj_name"]	=	UnderscoresToCamelCase(variables["fk_name"])+"Fk";
		variables["strMapping"]="<many-to-one class=\""+variables["full_name"]+"Dto\"\n\t column=\""+variables["fk_obj_name"]+"\" name=\""+variables["fk_obj_name"]+"\" not-null=\"false\" />";
		if(os.end() != os.find(variables["fk_name"]))
		{
			printer.Print(variables,"`strMapping`\n");
		}
	}
}
   


void HibernateHbmFileCodeGen::PrintMessage(io::Printer &printer,const Descriptor & message,bool enableBdir,std::string prefix) const 
{
	size_t pos=QualifiedJavaClassOrEnumName(message).find_last_of('.');
	printer.Print(" <class name=\"`package`.dto.`name`Dto\" table=\"`name`Info\">\n","package",QualifiedJavaClassOrEnumName(message).substr(0,pos),"name",UnqualifiedClassOrEnumOrFieldName(message));
	printer.Indent();

	//Now we generate Primary Key, assumption is Message MUST contain `name`Pk field, so validate that first
	const std::string cstrNamePK = UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message)) + "Pk";
	int fc = 0;
	for (; fc < message.field_count(); ++fc) 
	{
		if(cstrNamePK == VariableName(*message.field(fc)))
			break;
		//else not required
	}
	if(message.field_count() == fc)
	{
		throw "Critical Error: `name`Pk variable not found";
	}
	//`name`Pk field found, so continue
	printer.Print("<id name=\"`namePk`\" column=\"`namePk`\">\n","namePk",cstrNamePK);
	printer.Indent();
	printer.Print("<generator class=\"native\" />\n");
	printer.Outdent();
	printer.Print("</id>\n");
	for (int i = 0; i < message.field_count(); ++i) 
	{
		//Ignore `name`Pk as this is processed before
		if(cstrNamePK == VariableName(*message.field(i)))
			continue;

		//else process the field
		bool isComplex = false;

		const FieldDescriptor &field (*message.field(i) );
		map<std::string,std::string> variables;
		variables["name"]= VariableName(field);
		variables["Name"]=UnderscoresToCapitalizedCamelCase(field);
		variables["message_name"]=UnqualifiedClassOrEnumOrFieldName(message);
		variables["foreign_key"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
		variables["pojo_package_name"]=QualifiedJavaClassOrEnumName(message).substr(0,pos);
		variables["fullyqualified_pojo_class"]=variables["pojo_package_name"]+".dto."+variables["Name"]+"Dto";

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
				mylist.push_back(QualifiedJavaClassOrEnumName(newmessage));
				variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
				variables["index_column"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
				size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
				std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
				variables["qualified_class_name"]=actual_name;
				printer.Indent();
				printer.Print(variables,"<bag name=\"`name`\" cascade=\"all-delete-orphan\" lazy=\"false\">\n");
				printer.Indent();
				printer.Print(variables," <key column=\"`foreign_key`Fk\" />\n");
				printer.Print(variables," <one-to-many class=\"`qualified_class_name`.dto.`Childmessage`Dto\" />\n");
				printer.Outdent();
				printer.Print(variables,"</bag>\n");
				printer.Outdent();
			}
			else
			{
				printer.Print(variables,"<bag name=\"`name`\" cascade=\"all-delete-orphan\" lazy=\"false\">\n");
				printer.Indent();
				printer.Print(variables,"<key column=\"`foreign_key`Fk\" />\n");
				printer.Print(variables,"<one-to-many class=\"`fullyqualified_pojo_class`\" />\n");
				printer.Outdent();
				printer.Print(variables," </bag>\n");
			}
		}
		else
		{
			if(isComplex)
			{
				const Descriptor &newmessage(*field.message_type());
				mylist.push_back(QualifiedJavaClassOrEnumName(newmessage));
				variables["Childmessage"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
				variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(newmessage));
				size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
				std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
				variables["qualified_class_name"]=actual_name;
				printer.Print(variables,"<many-to-one name=\"`name`\" class=\"`qualified_class_name`.dto.`Childmessage`Dto\"\n");
				printer.Indent();
				printer.Print(variables,"column=\"`name`Fk\" not-null=\"true\" cascade=\"all\" unique=\"true\" lazy=\"false\"/>\n");
				printer.Outdent();
			}
			else
			{
				printer.Print(variables,"<property name=\"`name`\" column=\"`Name`\"/>\n");
			}
		}
	}
	//Below commented code is used to enable reverse many-to-one relationship, we do not need it at the monent
	//PrintComplexMessages(printer,message);
	printer.Print("\n</class>\n");
}


void HibernateHbmFileCodeGen::PrintMessages(io::Printer &printer,const FileDescriptor & file) const
{      
      ReadStdMapFromFile(im,"../temp/RepeatedFieldDependencyMapSet.txt");
      ReadStdSetFromFile(os,"../temp/HbmRootStore.txt");
      std::string package=file.package();
      size_t pos = package.find_last_of('.');
      std::string name = ReplaceDotWithSlash(package.substr(0,pos));
      printer.Print("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n");
      printer.Print("<!DOCTYPE hibernate-mapping PUBLIC\n");
      printer.Print("\"-//Hibernate/Hibernate Mapping DTD 3.0//EN\"\n");
      printer.Print("\"http://hibernate.sourceforge.net/hibernate-mapping-3.0.dtd\">\n");
      printer.Print("<hibernate-mapping>\n");
      printer.Indent();
      for (int i = 0; i < file.message_type_count(); ++i) 
         {
            const Descriptor & message(*file.message_type(i));
            std::string strHbmRoot=message.options().GetExtension(FluxMsgOrmRoot);
            size_t pl=QualifiedJavaClassOrEnumName(message).find_last_of('.');
            std::string actual_name=ReplaceDotWithSlash(QualifiedJavaClassOrEnumName(message).substr(0,pl));
           if(os.end() != os.find(UnqualifiedClassOrEnumOrFieldName(message)))
            {
                  PrintMessage(printer,*file.message_type(i),false,"");
            }
         }
      printer.Outdent();
      printer.Print("</hibernate-mapping>\n");
      mylist.clear();
        
}

bool HibernateHbmFileCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{                                   
	std::string cpp_filename ( file->name());
	size_t slashposition=cpp_filename.find_last_of ('/');
	size_t pos1 = cpp_filename.find_first_of ('.');
	std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
	size_t pf = sbstring.find_first_of ('.');
	std::string file_name=sbstring.substr(0,pf);
	scoped_ptr<io::ZeroCopyOutputStream> output(
	output_directory->Open(file_name+".hbm.xml")
	);

	io::Printer printer(output.get(), '`');
	PrintMessages(printer, *file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
                sleep(30);
	HibernateHbmFileCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
