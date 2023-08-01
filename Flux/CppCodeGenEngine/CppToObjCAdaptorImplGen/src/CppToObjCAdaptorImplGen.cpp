/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

#define COMP_NAME ""

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class CppToObjCAdaptorImplGen: public FluxCodeGenerator
{
	protected:
		void PrintDependencies(io::Printer &printer, const FileDescriptor & file) const ;
		void PrintStaticDependencies(io::Printer &printer, const FileDescriptor & file) const;
		void PrintDynamicAdaptorDependencies(io::Printer &printer, const Descriptor & message) const;
		void PrintDynamicObjCClassDependencies(io::Printer &printer, const Descriptor & message) const;

		std::string ObjCVariableGetterName(const FieldDescriptor & field, std::string objC_AccessPrefix) const;
		std::string CppVariableSetterName(const FieldDescriptor & field) const ;
		std::string CppComplexVariableGetterName(const FieldDescriptor & field) const ;
		std::string CppVariableCheckerName(const FieldDescriptor & field) const ;
		
		void PrintCppToObjCAdaptorImplBody(io::Printer &printer, const Descriptor & message) const;
		void PrintCppToObjCAdaptorImpl(io::Printer &printer, const Descriptor & message)const;
		void PrintMessages  (const FileDescriptor & file, io::Printer &printer) const;
		bool IsCodeGenRequired(const FileDescriptor& file)const;

		mutable std::set<std::string> responseMsgSet;
		mutable std::set<std::string> resolvedAdaptorDepFileNameSet;
		mutable std::set<std::string> resolvedObjCClasDepFileNameSet;

	public:
		CppToObjCAdaptorImplGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void CppToObjCAdaptorImplGen::PrintDependencies(io::Printer &printer, const FileDescriptor & file) const 
{
	//First Print Static Dependencies
	PrintStaticDependencies(printer, file);
	//All Dynamic dependencies are in the interface header file, just importing that is sufficient
	printer.Print("#import \"`FileName`.h\"\n","FileName",(GetFileNameFromFileDescriptor(&file) + "_CppToObjCAdaptor"));
}
void CppToObjCAdaptorImplGen::PrintStaticDependencies(io::Printer &printer, const FileDescriptor & file) const 
{
	map<std::string, std::string> variables;
	variables["FileName"] = GetFileNameFromFileDescriptor(&file);
	variables["ModelName"] = file.name();
	variables["copy_right"] = getenv("COPY_RIGHT")?getenv("COPY_RIGHT"):"Copyright (c) 2012 __MyCompanyName__. All rights reserved.";

	printer.Print("//\n");
	printer.Print(variables,"// `FileName`_CppToObjCAdaptor.mm\n");
	printer.Print(variables,"// Generated as Part of `ModelName`\n");
	printer.Print("// Created by Code Gen on Time Stamp same as File creation Time Stamp\n");
	printer.Print(variables,"// `copy_right`\n");
	printer.Print("//\n\n");
	printer.Print("#import \"FluxProtoObjCSupport.h\"\n");
}

std::string CppToObjCAdaptorImplGen::ObjCVariableGetterName(const FieldDescriptor & field, std::string objC_AccessPrefix) const 
{
	switch(field.type()) 
	{
		case FieldDescriptor::TYPE_STRING:
		{
			//String Type - Special Handelling
			//Sample Code: In addition, we need a NIL check
			//cppSearchSpecificAddressBookRequest.set_authenticationtoken([searchSpecificAddressBookRequest.authenticationToken UTF8String]);
			return std::string("[") + objC_AccessPrefix + VariableName(field) + " UTF8String]";
		}
		case FieldDescriptor::TYPE_INT32:
		{
			return ("[") + objC_AccessPrefix + VariableName(field) + " intValue]";
		}
		case FieldDescriptor::TYPE_INT64:
		{
			return ("[") + objC_AccessPrefix + VariableName(field) + " longLongValue]";
		}
		case FieldDescriptor::TYPE_UINT32:
		{
			return ("[") + objC_AccessPrefix + VariableName(field) + " unsignedIntValue]";
		}
		case FieldDescriptor::TYPE_UINT64:
		{
			return ("[") + objC_AccessPrefix + VariableName(field) + " unsignedLongLongValue]";
		}
		case FieldDescriptor::TYPE_FLOAT:
		{
			return ("[") + objC_AccessPrefix + VariableName(field) + " floatValue]";
		}
		case FieldDescriptor::TYPE_DOUBLE:
		{
			return ("[") + objC_AccessPrefix + VariableName(field) + " doubleValue]";
		}
		case FieldDescriptor::TYPE_BOOL:
		{
			return ("[") + objC_AccessPrefix + VariableName(field) + " boolValue]";
		}
		case FieldDescriptor::TYPE_MESSAGE:
		case FieldDescriptor::TYPE_GROUP:
		{
			//Complex Type
			throw "Impossible Bug, this method should be called only for simple types and strings";
		}
		default:
		{
			//Regular Simple Type
			//Sample Code: In addition, we need a NIL check
			//cppSearchSpecificAddressBookRequest.mutable_person()->set_age(searchSpecificAddressBookRequest.person.age);
			return objC_AccessPrefix + VariableName(field);
		}
	}
	return UnderscoresToCamelCase(field);
}

std::string CppToObjCAdaptorImplGen::CppVariableSetterName(const FieldDescriptor & field) const 
{
	return (std::string("set_") + field.name());
}

std::string CppToObjCAdaptorImplGen::CppComplexVariableGetterName(const FieldDescriptor & field) const 
{
	return (std::string("mutable_") + field.name());
}

std::string CppToObjCAdaptorImplGen::CppVariableCheckerName(const FieldDescriptor & field) const 
{
	return (std::string("has_") + field.name());
}

//map<std::string,std::string> variables pass by value on purpose, recursive implementation
void CppToObjCAdaptorImplGen::PrintCppToObjCAdaptorImplBody(io::Printer &printer, const Descriptor & message) const 
{	
	//in case we need multiple for loops we need unique loop counter variables
	std::string counterVar = GetUniqueIdentifierName();

	//Now the code gen, first get the objC object name and the cpp object name
	map<std::string,std::string> variables;
	variables["CamelCaseRequestVar"] = UnderscoresToCamelCase(message);
	variables["ObjC_AccessPrefix"] = variables["CamelCaseRequestVar"] + ".";

	variables["CppCamelCaseRequestVar"] = std::string("cpp_") + UnderscoresToCamelCase(message);
	variables["Cpp_AccessPrefix"] = variables["CppCamelCaseRequestVar"] + ".";

	for (int i = 0; i < message.field_count(); ++i)
	{
		bool isComplex = false;
		const FieldDescriptor &field ( *message.field(i) );
		map<std::string, std::string> private_variables = variables;

		private_variables["ObjC_VarName"]     = VariableName(field);
		private_variables["Cpp_VarName"]      = field.name();
		private_variables["counterVar"]		  = counterVar;
		private_variables["CppComplexVariableGetterName"] = CppComplexVariableGetterName(field);
		private_variables["CppVariableCheckerName"] = CppVariableCheckerName(field);

		switch (field.type())
		{
			case FieldDescriptor::TYPE_MESSAGE:
			case FieldDescriptor::TYPE_GROUP:
				private_variables["Cpp_type"] = QualifiedCppClassOrEnumName(*field.message_type()) + " ";
				private_variables["ObjC_type"] = UnqualifiedClassOrEnumOrFieldName(*field.message_type()) + " ";
				isComplex = true;
				break;
			case FieldDescriptor::TYPE_ENUM:
				private_variables["Cpp_type"] = QualifiedCppClassOrEnumName(*field.enum_type());
				private_variables["ObjC_type"] = UnqualifiedClassOrEnumOrFieldName(*field.enum_type()) + " ";
				break;
			default:
				private_variables["type"] = "";
		}

		if (field.is_repeated()) 
		{
			// Repeated field
			//Since this is a repeated field, we need to instantiate ObjC array first (only if cpp element count > 0)
			printer.Print(private_variables,"if(`Cpp_AccessPrefix``Cpp_VarName`_size() > 0)\n");
			printer.Indent();
			printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = [[NSMutableArray alloc] init];\n");
			printer.Outdent();
			//Now run loop and add as many elements as required
			printer.Print(private_variables,"for (int `counterVar` = 0; `counterVar` < `Cpp_AccessPrefix``Cpp_VarName`_size(); `counterVar`++)\n");
			printer.Print("{\n");
			printer.Indent();

			//We are inside the loop means we need to add an element irrespective
			printer.Print(private_variables,"[`ObjC_AccessPrefix``ObjC_VarName` addObject:[[`ObjC_type` alloc] init]];\n");
			if(isComplex)
			{
				//If complex:
				//Setup Child Vars
				map<std::string,std::string> child_variables;
				//Now call same generated overloaded method with objC and cpp objects
				child_variables["CppObj_AccessString"] = private_variables["Cpp_AccessPrefix"] + private_variables["CppComplexVariableGetterName"] +
													  "(" + private_variables["counterVar"] + ")";
				child_variables["ObjCObj_AccessString"] = "((" + private_variables["ObjC_type"] + "*)[" + private_variables["ObjC_AccessPrefix"] +
														private_variables["ObjC_VarName"] + " objectAtIndex:" + private_variables["counterVar"] + "])";
				printer.Print(child_variables,"if(0 != `CppObj_AccessString`)\n");
				printer.Print("{\n");
				printer.Indent();
					printer.Print(child_variables,"if(false == CppToObjCAdaptor(`ObjCObj_AccessString`, *`CppObj_AccessString`))\n");
					printer.Print("{\n");
					printer.Indent();
					printer.Print("//Conversion failed\n");
					printer.Print("return false;\n");
					printer.Outdent();
					printer.Print("}\n\n");
				printer.Outdent();
				printer.Print("}\n\n");
			}
			else //Simple Type / Enum
			{
				throw "Repeated of simple type not supported at the moment";
			}
			printer.Outdent();
			printer.Print("}\n");
		}
		else
		{
			map<std::string,std::string> child_variables;
			//complex or not, we need to check if field is present or not
			child_variables["CppObj_CheckerString"] = private_variables["Cpp_AccessPrefix"] + private_variables["CppVariableCheckerName"] + "()";
			printer.Print(child_variables,"if(`CppObj_CheckerString`)\n");
			printer.Print("{\n");
			printer.Indent();

			// Non repeated field
			if(isComplex)
			{
				//If complex:
				//Allocate the complextype first
				printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = [[`ObjC_type` alloc] init];\n");
				//Setup Child Vars
				child_variables["CppObj_AccessString"] = private_variables["Cpp_AccessPrefix"] + private_variables["CppComplexVariableGetterName"] + "()";
				child_variables["ObjCObj_AccessString"] = private_variables["ObjC_AccessPrefix"] + private_variables["ObjC_VarName"];
				//Now call generated overload
				printer.Print(child_variables,"if(false == CppToObjCAdaptor(`ObjCObj_AccessString`, *`CppObj_AccessString`))\n");
				printer.Print("{\n");
				printer.Indent();
				printer.Print("//Conversion failed\n");
				printer.Print("return false;\n");
				printer.Outdent();
				printer.Print("}\n");
			}
			else
			{
				//Finally the action on leaf

				//Sample Code: In addition, we need a NIL check
				//if(cppSearchSpecificAddressBookResponse.addressbook().has_longitude())
				// searchSpecificAddressBookResponse.addressBook.longitude = cppSearchSpecificAddressBookResponse.addressbook().longitude();
				switch (field.type())
				{
					case FieldDescriptor::TYPE_ENUM:
						printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = (`ObjC_type`)`Cpp_AccessPrefix``Cpp_VarName`();\n");
						break;
					case FieldDescriptor::TYPE_STRING:
						//String Type - Special Handelling

						//Sample Code: In addition, we need a NIL check
						//if(cppSearchSpecificAddressBookResponse.has_authenticationtoken())
						//	 searchSpecificAddressBookResponse.authenticationToken = [[NSString alloc] 
						//						initWithCString:(cppSearchSpecificAddressBookResponse.authenticationtoken().c_str()) encoding:(NSUTF8StringEncoding)];
						printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = [[NSString alloc] initWithCString:(`Cpp_AccessPrefix`mutable_`Cpp_VarName`()->c_str()) encoding:(NSUTF8StringEncoding)];\n");
						break;
					case FieldDescriptor::TYPE_INT32:
						printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = [NSNumber numberWithInt:`Cpp_AccessPrefix``Cpp_VarName`()];\n");
						break;
					case FieldDescriptor::TYPE_INT64:
						printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = [NSNumber numberWithLongLong:`Cpp_AccessPrefix``Cpp_VarName`()];\n");
						break;
					case FieldDescriptor::TYPE_UINT32:
						printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = [NSNumber numberWithUnsignedInt:`Cpp_AccessPrefix``Cpp_VarName`()];\n");
						break;
					case FieldDescriptor::TYPE_UINT64:
						printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = [NSNumber numberWithUnsignedLongLong:`Cpp_AccessPrefix``Cpp_VarName`()];\n");
						break;
					case FieldDescriptor::TYPE_FLOAT:
						printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = [NSNumber numberWithFloat:`Cpp_AccessPrefix``Cpp_VarName`()];\n");
						break;
					case FieldDescriptor::TYPE_DOUBLE:
						printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = [NSNumber numberWithDouble:`Cpp_AccessPrefix``Cpp_VarName`()];\n");
						break;
					case FieldDescriptor::TYPE_BOOL:
						printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = [NSNumber numberWithBool:`Cpp_AccessPrefix``Cpp_VarName`()];\n");
						break;
					default: //Some Supported Simple Type
						printer.Print(private_variables,"`ObjC_AccessPrefix``ObjC_VarName` = `Cpp_AccessPrefix``Cpp_VarName`()];\n");
				}
			}			
			printer.Outdent();
			printer.Print("}\n");
		}
	}
}

//No Recursion, just print this method body and that's it!!
void CppToObjCAdaptorImplGen::PrintCppToObjCAdaptorImpl(io::Printer &printer, const Descriptor & message)const
{
	map<std::string,std::string> variables;
	variables["RequestType"] = UnderscoresToCapitalizedCamelCase(message);
	variables["CamelCaseRequestVar"] = UnderscoresToCamelCase(message);
	variables["FullyQualifiedCppRequestType"] = QualifiedCppClassOrEnumName(message);
	variables["CppCamelCaseRequestVar"] = std::string("cpp_") + UnderscoresToCamelCase(message);
	
	printer.Print(variables,"bool CppToObjCAdaptor(`RequestType`* `CamelCaseRequestVar`, `FullyQualifiedCppRequestType`& `CppCamelCaseRequestVar`)\n");
	printer.Print(variables,"{\n");
	printer.Indent();

	PrintCppToObjCAdaptorImplBody(printer, message);

	printer.Print("return true;\n");
	printer.Outdent();
	printer.Print("}\n\n");
}

void CppToObjCAdaptorImplGen::PrintMessages(const FileDescriptor & file, io::Printer& printer) const 
{
	PrintDependencies(printer, file);

	//Now Print Body of local CPP Functions one per message that is a response
	for (int i = 0; i < file.message_type_count(); ++i)
	{
		const Descriptor &message = *file.message_type(i);
		if(responseMsgSet.end() != responseMsgSet.find(UnqualifiedClassOrEnumOrFieldName(message)))
		{
			//This message is in the responseMsgSet - generate code
			PrintCppToObjCAdaptorImpl(printer, message);
		}
	}
}

bool CppToObjCAdaptorImplGen::IsCodeGenRequired(const FileDescriptor& file)const
{
	ifstream iResponseMsgSetStoreFile("../temp/ResponseMsgSetStore.txt");
	if (iResponseMsgSetStoreFile)		
		ReadStdSetFromFile(responseMsgSet,"../temp/ResponseMsgSetStore.txt");
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor & message(*file.message_type(i));
		if(responseMsgSet.end() != responseMsgSet.find(UnqualifiedClassOrEnumOrFieldName(message)))
		{
		   //Even finding one message that is in the responseMsgSet is good enough to indicate generation required
		   return true;
		}
	}
	return false;
}

bool CppToObjCAdaptorImplGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{	
	//First Check if this file needs code Gen
	if(IsCodeGenRequired(*file))
	{
		std::string cppToObjCAdaptorName = "/"+ GetFileNameFromFileDescriptor(file) + "_CppToObjCAdaptor.mm";
		scoped_ptr<io::ZeroCopyOutputStream> cppToObjCAdaptorOutput(output_directory->Open(cppToObjCAdaptorName));
		io::Printer printer(cppToObjCAdaptorOutput.get(), '`');

		PrintMessages  (*file,printer);
	}	
	return true;
}


int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	CppToObjCAdaptorImplGen generator;
	return PluginMain(argc, argv, &generator);
}
