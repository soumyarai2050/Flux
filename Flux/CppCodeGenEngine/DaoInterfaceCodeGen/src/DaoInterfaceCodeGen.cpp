
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

class DaoInterfaceCodeGen: public FluxCodeGenerator 
{
	protected:
		void PrintMessages(io::Printer &printer, const FileDescriptor & file) const;
		void PrintStaticDependencies(io::Printer &printer, const FileDescriptor & file) const;
		void PrintDynamicDependencies(io::Printer &printer, const Descriptor & message, OrmCreateUpdateOrDeleteClasses& ormCreateUpdateOrDeleteClasses) const;
		void PrintDynamicDependencies(io::Printer &printer, const Descriptor & message, OrmReadRespClasses& ormReadRespClasses) const;
		void PrintDtoDependencies(io::Printer &printer,const Descriptor & message,std::string childQuaryName) const;
		void PopulateRequestResponseCodeGenData(map<std::string,std::string>& variables, const Descriptor & message)const;
		void PopulateSearchCodeGenData(map<std::string,std::string>& variables, const OrmReadRespClass& ormReadRespClass, const Descriptor & message)const;
		void PrintSearchInterface(io::Printer &printer, const Descriptor & message, OrmReadRespClasses& ormReadRespClasses) const ;
		void PopulateSaveOrUpdateCodeGenData(map<std::string,std::string>& variables, const OrmCreateUpdateOrDeleteClass& ormCreateUpdateOrDeleteClass, const Descriptor & message)const;
        void PrintSaveOrUpdateInterface(io::Printer &printer, map<std::string,std::string>& variables) const ;
		void PrintCreateUpdateOrDeleteInterface(io::Printer &printer, const Descriptor & message, OrmCreateUpdateOrDeleteClasses& ormCreateUpdateOrDeleteClasses) const;
	public:
		DaoInterfaceCodeGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void DaoInterfaceCodeGen::PrintStaticDependencies(io::Printer &printer, const FileDescriptor & file) const 
{
	map<std::string,std::string> variables;
	//find package name where dto files resides
	std::string package=file.package();
	size_t p = package.find_last_of('.');
	//find package name for the java file generated
	std::string name = package.substr(0,p);
	printer.Print("package `name`.dao;\n","name",name);
}

void DaoInterfaceCodeGen::PrintDynamicDependencies(io::Printer &printer, const Descriptor & message, OrmCreateUpdateOrDeleteClasses& ormCreateUpdateOrDeleteClasses) const 
{
	for(unsigned int i = 0; i< ormCreateUpdateOrDeleteClasses.size(); i++)
	{
		std::string strFluxMsgOrmRsp = ormCreateUpdateOrDeleteClasses[i].getPersistenceClassTypeName();
		if(0!=strFluxMsgOrmRsp.length())
		{
			if( strFluxMsgOrmRsp==UnqualifiedClassOrEnumOrFieldName(message))
			{
				std::string qualifed_name=QualifiedJavaClassOrEnumName(message);
				size_t p=qualifed_name.find_last_of('.');
				std::string pojo_clas=qualifed_name.replace(p,1,".dto.");
				printer.Print("import `name`Dto;\n","name",pojo_clas);
			}
			else
			{
				PrintDtoDependencies(printer,message,strFluxMsgOrmRsp);
			}
		}
	}
}

void DaoInterfaceCodeGen::PrintDynamicDependencies(io::Printer &printer, const Descriptor & message, OrmReadRespClasses& ormReadRespClasses) const 
{
	for(unsigned int i = 0; i< ormReadRespClasses.size(); i++)
	{
		std::string strFluxMsgOrmRsp = ormReadRespClasses[i].getRespTypeName();
		{
			if( strFluxMsgOrmRsp==UnqualifiedClassOrEnumOrFieldName(message))
			{
				std::string qualifed_name=QualifiedJavaClassOrEnumName(message);
				size_t p=qualifed_name.find_last_of('.');
				std::string pojo_clas=qualifed_name.replace(p,1,".dto.");
				printer.Print("import `name`Dto;\n","name",pojo_clas);
			}
			else
			{
				PrintDtoDependencies(printer,message,strFluxMsgOrmRsp);
			}
		}
	}
}

void DaoInterfaceCodeGen::PrintDtoDependencies(io::Printer &printer,const Descriptor & message,std::string childQuaryName) const 
{
	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		map<std::string,std::string> variables;
		const FieldDescriptor &field (*message.field(i) );
		variables["name"]          = VariableName(field);
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
				if(childQuaryName==UnqualifiedClassOrEnumOrFieldName(newmessage))
				{
					std::string qualifed_name=QualifiedJavaClassOrEnumName(newmessage);
					size_t p=qualifed_name.find_last_of('.');
					std::string pojo_clas=qualifed_name.replace(p,1,".dto.");
					printer.Print("import `name`Dto;\n","name",pojo_clas);
				}
				else
				PrintDtoDependencies(printer,newmessage,childQuaryName);
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
				if(childQuaryName==UnqualifiedClassOrEnumOrFieldName(newmessage))
				{
					std::string qualifed_name=QualifiedJavaClassOrEnumName(newmessage);
					size_t p=qualifed_name.find_last_of('.');
					std::string pojo_clas=qualifed_name.replace(p,1,".dto.");
					printer.Print("import `name`Dto;\n","name",pojo_clas);
				}
				else
				{
					PrintDtoDependencies(printer,newmessage,childQuaryName);
				}
			}//No else required, simple types dont need import
		}
	}
}

void DaoInterfaceCodeGen::PopulateRequestResponseCodeGenData(map<std::string,std::string>& variables, const Descriptor & message)const
{
	//Request
	//Get any additional fields
	variables["RequestType"] = GetComponentArtifactName(message,DTO_COMP_NAME);
	variables["RequestTypePkg"] = GetComponentPackageName(message, DTO_COMP_NAME);
	variables["FullyQualifiedRequestType"] = variables["RequestTypePkg"] + "." + variables["RequestType"];
	variables["CamelCaseRequestType"] = UnderscoresToCamelCase(message);
	variables["CamelCaseRequestVar"] = GetComponentVariableName(variables["CamelCaseRequestType"], DTO_COMP_NAME);

	//Response
	std::string respTypeName = ResponseNameCheckerAndGenerator(message);
	if(0 == respTypeName.length())
		throw "Bug! - Not possible situation - PopulateResponseCodeGenData called when FluxMsgRsp is not set!!";
	const Descriptor & respTypeMessage = *(GetNestedMessageDescriptorFromFile(respTypeName,*(message.file())));
	variables["RespType"] = GetComponentArtifactName(respTypeMessage,DTO_COMP_NAME);
	variables["CamelCaseRespType"] = UnderscoresToCamelCase(variables["RespType"]);
	variables["RespTypePkg"] = GetComponentPackageName(respTypeMessage, DTO_COMP_NAME);
	variables["FullyQualifiedRespType"] = variables["RespTypePkg"] + "." + variables["RespType"];
}

void DaoInterfaceCodeGen::PopulateSearchCodeGenData(map<std::string,std::string>& variables, const OrmReadRespClass& ormReadRespClass, const Descriptor & message)const
{
	const Descriptor & respTypeMessage = *(GetNestedMessageDescriptorFromFile(ormReadRespClass.getRespTypeName(),*(message.file())));
	variables["ORMRespType"] = respTypeMessage.name();
	variables["ORMRespCompType"] = GetComponentArtifactName(respTypeMessage,DTO_COMP_NAME);
	variables["ORMRespCompTypePkg"] = GetComponentPackageName(respTypeMessage, DTO_COMP_NAME);
	variables["FullyQualifiedORMRespCompType"] = variables["ORMRespCompTypePkg"] + "." + variables["ORMRespCompType"];
	variables["ORMRespVar"] = UnderscoresToCamelCase(ormReadRespClass.getRespVarName());
	variables["ORMRespCompVar"] = GetComponentVariableName(variables["ORMRespVar"],DTO_COMP_NAME);
	variables["CapitalizedCamelCaseORMRespVar"] = ormReadRespClass.getCapitalizedCamelCaseRespVarName();
}

void DaoInterfaceCodeGen::PopulateSaveOrUpdateCodeGenData(map<std::string,std::string>& variables, const OrmCreateUpdateOrDeleteClass& ormCreateUpdateOrDeleteClass, const Descriptor & message)const
{
	const Descriptor & persistenceClassTypeMessage = *(GetNestedMessageDescriptorFromFile(ormCreateUpdateOrDeleteClass.getPersistenceClassTypeName(),*(message.file())));
	variables["PersistenceClassCompType"] = GetComponentArtifactName(persistenceClassTypeMessage,DTO_COMP_NAME);
	variables["PersistenceClassCompTypePkg"] = GetComponentPackageName(persistenceClassTypeMessage, DTO_COMP_NAME);
	variables["FullyQualifiedPersistenceClassCompType"] = variables["PersistenceClassCompTypePkg"] + "." + variables["PersistenceClassCompType"];
	variables["PersistenceClassVar"] = UnderscoresToCamelCase(ormCreateUpdateOrDeleteClass.getPersistenceClassVarName());
	variables["CapitalizedCamelCasePersistenceClassVar"] = ormCreateUpdateOrDeleteClass.getCapitalizedCamelCasePersistenceClassVarName();
	variables["PersistenceClassCompVar"] = GetComponentVariableName(variables["PersistenceClassVar"],DTO_COMP_NAME);
	variables["CapitalizedCamelCasePersistenceClassCompVar"] = GetComponentVariableName(ormCreateUpdateOrDeleteClass.getCapitalizedCamelCasePersistenceClassVarName(), DTO_COMP_NAME);
}

void DaoInterfaceCodeGen::PrintSaveOrUpdateInterface(io::Printer &printer, map<std::string,std::string>& variables) const 
{
	printer.Print(variables,"public abstract void saveOrUpdate(`PersistenceClassCompType` `PersistenceClassCompVar`);\n");
}

void DaoInterfaceCodeGen::PrintSearchInterface(io::Printer &printer, const Descriptor & message, OrmReadRespClasses& ormReadRespClasses) const 
{
	map<std::string,std::string> variables;
	PopulateRequestResponseCodeGenData(variables,message);

	printer.Print(variables,"public abstract `FullyQualifiedRespType`  `CamelCaseRequestType`(`FullyQualifiedRequestType` `CamelCaseRequestVar`);\n");
}

void DaoInterfaceCodeGen::PrintCreateUpdateOrDeleteInterface(io::Printer &printer, const Descriptor & message, OrmCreateUpdateOrDeleteClasses& ormCreateUpdateOrDeleteClasses) const 
{
	//Print CreateUpdateOrDelete Method
	map<std::string,std::string> variables;
	PopulateRequestResponseCodeGenData(variables,message);

	//Generate code for all saveOrUpdate (top level classes) candidates in this message
	for(unsigned int i = 0; i < ormCreateUpdateOrDeleteClasses.size(); i++)
	{
		map<std::string,std::string> inVariables = variables;
		PopulateSaveOrUpdateCodeGenData(inVariables,ormCreateUpdateOrDeleteClasses[i],message);
		//Now we have all that we need, lets generate PrintSaveOrUpdateInterface first
		PrintSaveOrUpdateInterface(printer,inVariables);
	}
	
	printer.Print(variables,"public abstract `FullyQualifiedRespType` `CamelCaseRequestType`(`FullyQualifiedRequestType` `CamelCaseRequestVar`);\n");
}

void DaoInterfaceCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
{
	//First Print Static Dependencies
	PrintStaticDependencies(printer, file);
	//Print Dynamic Dependencies
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor & message(*file.message_type(i));
		OrmReadRespClasses ormReadRespClasses(message);
		OrmCreateUpdateOrDeleteClasses ormCreateUpdateOrDeleteClasses(message);
		
		if(ormReadRespClasses.IsOptionSet())
		{
			PrintDynamicDependencies(printer, message, ormReadRespClasses);
		}
		else if(ormCreateUpdateOrDeleteClasses.IsOptionSet())
		{
			PrintDynamicDependencies(printer, message, ormCreateUpdateOrDeleteClasses);
		}//else not required, ignore this message, this is of no interest to us.
	}

	//Open the main class
	printer.Print("\npublic interface I`file_name`Dao\n{\n","file_name",GetFileNameFromFileDescriptor(&file));
	printer.Indent();

	//Print HBM saveOrUpdate or search
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor & message(*file.message_type(i));
		OrmReadRespClasses ormReadRespClasses(message);
		OrmCreateUpdateOrDeleteClasses ormCreateUpdateOrDeleteClasses(message);
		
		if(ormReadRespClasses.IsOptionSet())
		{
			PrintSearchInterface(printer, message, ormReadRespClasses);
		}
		else if(ormCreateUpdateOrDeleteClasses.IsOptionSet())
		{
			PrintCreateUpdateOrDeleteInterface(printer, message, ormCreateUpdateOrDeleteClasses);
		}//else not required, ignore this message, this is of no interest to us.
	}
	printer.Outdent();
	printer.Print("\n}\n");

}


bool DaoInterfaceCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{

	scoped_ptr<io::ZeroCopyOutputStream> output(
	output_directory->Open((GetPackageDirectoryName(file) + "/" + DAO_COMP_NAME + "/I" + GetJavaComponentFileName(*file,DAO_COMP_NAME)))
	);

	io::Printer printer(output.get(), '`');
	PrintMessages(printer, *file);
	return true;
}



int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	DaoInterfaceCodeGen generator;
	return PluginMain(argc, argv, &generator);
}

