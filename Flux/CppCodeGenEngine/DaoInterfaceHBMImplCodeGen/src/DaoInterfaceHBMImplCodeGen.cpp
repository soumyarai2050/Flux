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

class DaoInterfaceHBMImplCodeGen: public FluxCodeGenerator 
{
	protected:
		void PrintMessages(io::Printer &printer, const FileDescriptor & file) const;
		void PrintStaticDependencies(io::Printer &printer, const FileDescriptor & file) const;
		void PrintDynamicDependencies(io::Printer &printer, const Descriptor & message, OrmCreateUpdateOrDeleteClasses& ormCreateUpdateOrDeleteClasses) const;
		void PrintDynamicDependencies(io::Printer &printer, const Descriptor & message, OrmReadRespClasses& ormReadRespClasses) const;
		void PrintDtoDependencies(io::Printer &printer,const Descriptor & message,std::string childQuaryName) const;
		void PopulateRequestResponseCodeGenData(map<std::string,std::string>& variables, const Descriptor & message)const;
		void PopulateSearchCodeGenData(map<std::string,std::string>& variables, const OrmReadRespClass& ormReadRespClass, const Descriptor & message)const;
		void PrintHBMSearchImpl(io::Printer &printer, const Descriptor & message, OrmReadRespClasses& ormReadRespClasses) const ;
		void PopulateSaveOrUpdateCodeGenData(map<std::string,std::string>& variables, const OrmCreateUpdateOrDeleteClass& ormCreateUpdateOrDeleteClass, const Descriptor & message)const;
        void PrintHBMSaveOrUpdateImpl(io::Printer &printer, map<std::string,std::string>& variables) const ;
		void PrintHBMCreateUpdateOrDeleteImpl(io::Printer &printer, const Descriptor & message, OrmCreateUpdateOrDeleteClasses& ormCreateUpdateOrDeleteClasses) const;
	public:
		DaoInterfaceHBMImplCodeGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void DaoInterfaceHBMImplCodeGen::PrintStaticDependencies(io::Printer &printer, const FileDescriptor & file) const 
{
	std::string file_name=GetFileNameFromFileDescriptor(&file);
	map<std::string,std::string> variables;
	//find package name where dto files resides
	variables["ClassName"]=file.package();
	std::string package=file.package();
	size_t p = package.find_last_of('.');
	//find package name for the java file generated
	std::string name = package.substr(0,p);
	printer.Print("package `name`.dao.impl;\n","name",name);
	printer.Print("import `name`.dao.*;\n","name",name);
	printer.Print("import static `name`.constants.I`ProjectName`Constants.ADD_SUCCESS;\n",
				   "name",name,"ProjectName",GetProjectName());
	
	printer.Print("import java.util.List;\n");
	printer.Print("import java.util.Random;\n");
	printer.Print("import org.hibernate.Criteria;\n");
	
	printer.Print("import org.hibernate.criterion.Criterion;\n");
	printer.Print("import org.hibernate.criterion.Expression;\n");
	printer.Print("import org.hibernate.criterion.LogicalExpression;\n");
	
	printer.Print("import org.hibernate.criterion.MatchMode;\n");
	
	printer.Print("import org.hibernate.criterion.Projections;\n");
	
	printer.Print("import org.hibernate.criterion.Restrictions;\n");
	printer.Print("import org.springframework.orm.hibernate3.HibernateTemplate;\n");
	printer.Print("import org.springframework.orm.hibernate3.support.HibernateDaoSupport;\n");
	printer.Print(variables,"import `ClassName`.*;\n\n");
}

void DaoInterfaceHBMImplCodeGen::PrintDynamicDependencies(io::Printer &printer, const Descriptor & message, OrmCreateUpdateOrDeleteClasses& ormCreateUpdateOrDeleteClasses) const 
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

void DaoInterfaceHBMImplCodeGen::PrintDynamicDependencies(io::Printer &printer, const Descriptor & message, OrmReadRespClasses& ormReadRespClasses) const 
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

void DaoInterfaceHBMImplCodeGen::PrintDtoDependencies(io::Printer &printer,const Descriptor & message,std::string childQuaryName) const 
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

void DaoInterfaceHBMImplCodeGen::PopulateRequestResponseCodeGenData(map<std::string,std::string>& variables, const Descriptor & message)const
{
	//Request
	//Get any additional fields
	variables["RequestType"] = GetComponentArtifactName(message,DTO_COMP_NAME);
	variables["RequestTypePkg"] = GetComponentPackageName(message, DTO_COMP_NAME);
	variables["FullyQualifiedRequestType"] = variables["RequestTypePkg"] + "." + variables["RequestType"];
	variables["CamelCaseRequestType"] = UnderscoresToCamelCase(message);
	variables["CamelCaseReqsCompVar"] = GetComponentVariableName(variables["CamelCaseRequestType"], DTO_COMP_NAME);

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

void DaoInterfaceHBMImplCodeGen::PopulateSearchCodeGenData(map<std::string,std::string>& variables, const OrmReadRespClass& ormReadRespClass, const Descriptor & message)const
{
	const Descriptor & respTypeMessage = *(GetNestedMessageDescriptorFromFile(ormReadRespClass.getRespTypeName(),*(message.file())));
	variables["ORMRespType"] = respTypeMessage.name();
	variables["ORMRespTypePkg"] = PackageName(respTypeMessage);
	variables["FullyQualifiedORMRespType"] = variables["ORMRespTypePkg"] + "." + variables["ORMRespType"];
	variables["ORMRespCompType"] = GetComponentArtifactName(respTypeMessage,DTO_COMP_NAME);
	variables["ORMRespCompTypePkg"] = GetComponentPackageName(respTypeMessage, DTO_COMP_NAME);
	variables["FullyQualifiedORMRespCompType"] = variables["ORMRespCompTypePkg"] + "." + variables["ORMRespCompType"];
	variables["ORMRespVar"] = UnderscoresToCamelCase(ormReadRespClass.getRespVarName());
	variables["ORMRespCompVar"] = GetComponentVariableName(variables["ORMRespVar"],DTO_COMP_NAME);
	variables["CapitalizedCamelCaseORMRespVar"] = ormReadRespClass.getCapitalizedCamelCaseRespVarName();
}

void DaoInterfaceHBMImplCodeGen::PopulateSaveOrUpdateCodeGenData(map<std::string,std::string>& variables, const OrmCreateUpdateOrDeleteClass& ormCreateUpdateOrDeleteClass, const Descriptor & message)const
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

void DaoInterfaceHBMImplCodeGen::PrintHBMSaveOrUpdateImpl(io::Printer &printer, map<std::string,std::string>& variables) const 
{
	printer.Print("\n@Override\n");
	printer.Print(variables,"public void saveOrUpdate(`PersistenceClassCompType` `PersistenceClassCompVar`)\n");
	printer.Print("{\n");
	printer.Indent();
	printer.Print("HibernateTemplate template = getHibernateTemplate();\n");
	printer.Print(variables,"template.saveOrUpdate(`PersistenceClassCompVar`);\n");
	printer.Outdent(); 
	printer.Print("}\n");
}

void DaoInterfaceHBMImplCodeGen::PrintHBMSearchImpl(io::Printer &printer, const Descriptor & message, OrmReadRespClasses& ormReadRespClasses) const 
{
	map<std::string,std::string> variables;
	PopulateRequestResponseCodeGenData(variables,message);

	printer.Print("\n@Override\n");
	printer.Print(variables,"public `FullyQualifiedRespType`  `CamelCaseRequestType`(`FullyQualifiedRequestType` `CamelCaseReqsCompVar`)\n");
	printer.Print("{\n");
	printer.Indent();
		printer.Print(variables,"`FullyQualifiedRespType` `CamelCaseRespType` = new `FullyQualifiedRespType`();\n");
		//Here check if the ORM response is mapped to repeat type.
		//Note: ATM either all members are repeat or none are, Check and find out:
		if(ormReadRespClasses.IsRepeatType())
		{
			printer.Print(variables,"Integer rowCount = (Integer)getCriteria(`CamelCaseReqsCompVar`).setProjection(Projections.rowCount()).uniqueResult();\n");
			printer.Print(variables,"Integer pageSize = `CamelCaseReqsCompVar`.getPageSize();\n");
			printer.Print(variables,"Integer pageNumber = `CamelCaseReqsCompVar`.getPageNumber();\n");

			for(unsigned int i = 0; i < ormReadRespClasses.size(); i++)
			{
				//Repeat From here
				map<std::string,std::string> inVariables = variables;
				PopulateSearchCodeGenData(inVariables,ormReadRespClasses[i], message);
				printer.Print(inVariables,"Criteria `ORMRespVar`Criteria = getCriteria(`CamelCaseReqsCompVar`);\n");
				
				printer.Print("if(pageSize!=null && pageNumber!=null)\n");
				printer.Print("{\n");
				printer.Indent();
					printer.Print(inVariables,"`ORMRespVar`Criteria.setFirstResult(pageSize * (pageNumber - 1));\n");
					printer.Print(inVariables,"`ORMRespVar`Criteria.setMaxResults(pageSize);\n");
				printer.Outdent();
				printer.Print("}\n");
				printer.Print(inVariables,"List<`FullyQualifiedORMRespCompType`> `ORMRespCompVar`List = `ORMRespVar`Criteria.list();\n");
				printer.Print(inVariables,"`CamelCaseRespType`.set`CapitalizedCamelCaseORMRespVar`(`ORMRespCompVar`List);\n");
				//Repeat up until here
			}
		}
		else//non repeat rmReadRespClasses handling
		{
			//TODO: May need improvement
			for(unsigned int i = 0; i < ormReadRespClasses.size(); i++)
			{
				//Repeat From here
				map<std::string,std::string> inVariables = variables;
				PopulateSearchCodeGenData(inVariables,ormReadRespClasses[i], message);
				printer.Print(inVariables,"Criteria `ORMRespVar`Criteria = getCriteria(`CamelCaseReqsCompVar`);\n");

				printer.Print(inVariables,"`FullyQualifiedORMRespCompType` `ORMRespCompVar` = (`ORMRespCompType`)`ORMRespVar`Criteria.uniqueResult();\n");
				printer.Print(inVariables,"`CamelCaseRespType`.set`CapitalizedCamelCaseORMRespVar`(`ORMRespCompVar`);\n");
				//Repeat up until here
			}
		}
		
		printer.Print(variables,"return `CamelCaseRespType`;\n");
	printer.Outdent();
	printer.Print("}\n");
		
	//Now add the getCriteria Method
	printer.Print("\n");
	printer.Print(variables,"private Criteria getCriteria(`FullyQualifiedRequestType` `CamelCaseReqsCompVar`)\n");
	printer.Print(variables,"{\n");
	printer.Indent();
	for(unsigned int i = 0; i < ormReadRespClasses.size(); i++)
	{
		map<std::string,std::string> inVariables = variables;
		PopulateSearchCodeGenData(inVariables,ormReadRespClasses[i], message);

		printer.Print(inVariables,"Criteria criteria = getSession().createCriteria(`FullyQualifiedORMRespCompType`.class,\"`ORMRespCompVar`\");\n");
		printer.Print(inVariables,"//TODO: 'Multiple return statements' Review and Fix This!!\n");
		if(!ormReadRespClasses.IsRepeatType())
		{
			printer.Print("criteria.setMaxResults(1);\n");
		}
		printer.Print(inVariables,"return criteria;\n");
	}
	printer.Outdent();
	printer.Print("}\n");
}

void DaoInterfaceHBMImplCodeGen::PrintHBMCreateUpdateOrDeleteImpl(io::Printer &printer, const Descriptor & message, OrmCreateUpdateOrDeleteClasses& ormCreateUpdateOrDeleteClasses) const 
{
	//Print CreateUpdateOrDelete Method
	map<std::string,std::string> variables;
	PopulateRequestResponseCodeGenData(variables,message);

	//Generate code for all saveOrUpdate (top level classes) candidates in this message
	for(unsigned int i = 0; i < ormCreateUpdateOrDeleteClasses.size(); i++)
	{
		map<std::string,std::string> inVariables = variables;
		PopulateSaveOrUpdateCodeGenData(inVariables,ormCreateUpdateOrDeleteClasses[i],message);
		//Now we have all that we need, lets generate PrintHBMSaveOrUpdateImpl first
		PrintHBMSaveOrUpdateImpl(printer,inVariables);
	}

	
	printer.Print("\n@Override\n");
	printer.Print(variables,"public `FullyQualifiedRespType` `CamelCaseRequestType`(`FullyQualifiedRequestType` `CamelCaseReqsCompVar`)\n");
	printer.Print("{\n");
	printer.Indent();
	//Gen code for all ORM mapped classes
	for(unsigned int i = 0; i < ormCreateUpdateOrDeleteClasses.size(); i++)
	{
		map<std::string,std::string> inVariables = variables;

		PopulateSaveOrUpdateCodeGenData(inVariables,ormCreateUpdateOrDeleteClasses[i],message);
		printer.Print(inVariables, "`FullyQualifiedPersistenceClassCompType` `PersistenceClassCompVar` =  `CamelCaseReqsCompVar`.get`CapitalizedCamelCasePersistenceClassVar`();\n");
		printer.Print(inVariables, "saveOrUpdate(`PersistenceClassCompVar`);\n");
		printer.Print(inVariables, "`FullyQualifiedRespType` `CamelCaseRespType` = new `FullyQualifiedRespType`();\n");
	}
	
	//Now Print Standard Authentication token 
	//TODO: At this point Authentication token, plus Action Result are mandatory in response, later some logic (authentication token) should move to Service layer
	printer.Print("Random random = new Random(System.currentTimeMillis());\n");
	printer.Print(variables, "`CamelCaseRespType`.setAuthenticationToken(\"\" + random.nextLong());\n");

	const Descriptor & respTypeMessage = *(GetNestedMessageDescriptorFromFile(ResponseNameCheckerAndGenerator(message),*(message.file())));

	//Finally Search and Print Action Result
	bool actionResultFound = false;
	for (int i = 0; i < respTypeMessage.field_count(); ++i) 
	{
		const FieldDescriptor &field ( *respTypeMessage.field(i) );
		map<std::string,std::string> inVariables = variables;
		if( field.type() == FieldDescriptor::TYPE_MESSAGE && field.message_type()->name() == "ActionResult" )
		{
			actionResultFound = true;
			const Descriptor &resultTypeMessage(*field.message_type());
			inVariables["ResultType"] = field.message_type()->name();
			inVariables["CompResultType"] = GetComponentArtifactName(resultTypeMessage,DTO_COMP_NAME);
			inVariables["CamelCaseCompResultType"] = UnderscoresToCamelCase(inVariables["CompResultType"]);
			inVariables["CompResultTypePkg"] = GetComponentPackageName(resultTypeMessage, DTO_COMP_NAME);
			inVariables["FullyQualifiedCompResultType"] = inVariables["CompResultTypePkg"] + "." + inVariables["CompResultType"];
			printer.Print(inVariables,"`FullyQualifiedCompResultType` `CamelCaseCompResultType` = new `FullyQualifiedCompResultType`();\n");
			
			printer.Print(inVariables,"`CamelCaseCompResultType`.setResult(true);\n");
			printer.Print(inVariables,"`CamelCaseCompResultType`.setDescription(ADD_SUCCESS);\n");
			printer.Print(inVariables,"`CamelCaseRespType`.set`ResultType`(`CamelCaseCompResultType`);\n");
			printer.Print(inVariables,"return `CamelCaseRespType`;\n");
			break;
		}
	}	
	if(!actionResultFound)
		throw "Mandatory ActionResult Not Found in message!!";
	printer.Outdent();
	printer.Print("}\n");



}

void DaoInterfaceHBMImplCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
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
	printer.Print("\npublic class `file_name`DaoImpl extends HibernateDaoSupport implements I`file_name`Dao\n{\n","file_name",GetFileNameFromFileDescriptor(&file));
	printer.Indent();

	//Print HBM saveOrUpdate or search
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor & message(*file.message_type(i));
		OrmReadRespClasses ormReadRespClasses(message);
		OrmCreateUpdateOrDeleteClasses ormCreateUpdateOrDeleteClasses(message);
		
		if(ormReadRespClasses.IsOptionSet())
		{
			PrintHBMSearchImpl(printer, message, ormReadRespClasses);
		}
		else if(ormCreateUpdateOrDeleteClasses.IsOptionSet())
		{
			PrintHBMCreateUpdateOrDeleteImpl(printer, message, ormCreateUpdateOrDeleteClasses);
		}//else not required, ignore this message, this is of no interest to us.
	}
	printer.Outdent();
	printer.Print("\n}\n");

}


bool DaoInterfaceHBMImplCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	std::string componentName = DAO_COMP_NAME "Impl";
	std::string fullPathFileName = GetPackageDirectoryName(file) + "/" + DAO_COMP_NAME + "/impl/" + GetJavaComponentFileName(*file,componentName);
	scoped_ptr<io::ZeroCopyOutputStream> output(
	output_directory->Open(fullPathFileName)
	);

	io::Printer printer(output.get(), '`');
	PrintMessages(printer, *file);
	return true;
}



int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	DaoInterfaceHBMImplCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
