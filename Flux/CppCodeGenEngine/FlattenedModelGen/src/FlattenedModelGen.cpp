/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-1
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include<map>
#include<set>
#include<list>
#include<deque>

#include <boost/serialization/vector.hpp>
#include <boost/serialization/set.hpp>

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class FlattenedModelGen: public FluxCodeGenerator 
{
	protected:
		std::string GetConflictFreeFieldName(const FieldDescriptor &field, 
											   std::set<std::string>& fieldNameCollisionSet,
											   std::deque<std::string>& fieldParentDeque) const;
		void PrintMessage(io::Printer &printer,const FileDescriptor & file, const Descriptor & message,
							 std::set<std::string>& fieldNameCollisionSet, 
							 std::deque<std::string>& fieldParentDeque, unsigned int& childStartFieldNumber) const ;
		void PrintMessages(io::Printer &printer, const FileDescriptor & file) const;
		void PrintEnumType(io::Printer &printer,const EnumDescriptor & enummessage) const;

		//Options
		std::string GetFieldDefaultValueOptionString(const FieldDescriptor & field)const;
		std::string GetFieldOptionsAsString(io::Printer &printer, const FieldDescriptor & field) const;
		void PrintMessageOptions(io::Printer &printer, const Descriptor & message) const;
		void PrintFileOptions(io::Printer &printer, const FileDescriptor & file) const;
		//Dependencise
		void PopulateMessageDependencies(io::Printer &printer,const FileDescriptor & file, const Descriptor & message, 
									 std::set <std::string>& dependencyNameSet, const std::string& strCurrentFile) const;
		void PopulateFileDependencies(io::Printer &printer, const FileDescriptor & file, 
											std::set <std::string>& dependencyNameSet) const;
		void PrintDependencies(io::Printer &printer, const FileDescriptor & file) const;
		bool IsProtoGenRequired(const FileDescriptor& file) const;

	public:
		mutable std::set<std::string> noExpandMsgDbSet;
		mutable std::set<std::string> hbmRootStoreSet;
		mutable std::map<std::string, std::set<std::string>* > extensionStore;

		FlattenedModelGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

std::string FlattenedModelGen::GetConflictFreeFieldName(const FieldDescriptor &field, 
									   std::set<std::string>& fieldNameCollisionSet,
									   std::deque<std::string>& fieldParentDeque) const 
{
	std::string strFieldName = ToLowerCaseUnderscoreSeparated(field.name());
	std::set<std::string>::iterator it = fieldNameCollisionSet.find(strFieldName);
	if(fieldNameCollisionSet.end() == it)
	{
		//This name is coming for first time
		fieldNameCollisionSet.insert(strFieldName);
		//Just return as is
	}
	else
	{
		//We have hit a name collision, put parent suffix logic in action
		std::deque<std::string>::reverse_iterator rit = fieldParentDeque.rbegin();
		for( ; rit != fieldParentDeque.rend(); rit++)
		{
			strFieldName = (*rit) + "_" + strFieldName;//Collision detected at root may cause variable name to be _variable
			std::set<std::string>::iterator tempIt = fieldNameCollisionSet.find(strFieldName);
			if(fieldNameCollisionSet.end() == tempIt)
			{
				//This name is coming for first time, assign this and break;
				fieldNameCollisionSet.insert(strFieldName);
				//Just break, strFieldName will be returned
				break;
			}//else not required, still in collision, continue in loop until resolved
		}
		if(rit == fieldParentDeque.rend())
		{
			//Code should never reach here, more for bug identification
			throw "Impossible Condition - Could not resolve collision with parent name";
		}
	}
	return strFieldName;
}
void FlattenedModelGen::PrintMessage(io::Printer &printer,const FileDescriptor & file, const Descriptor & message, 
									   std::set<std::string>& fieldNameCollisionSet,
									   std::deque<std::string>& fieldParentDeque,
									   unsigned int& childStartFieldNumber) const 
{
	unsigned int myStartFieldNumber = childStartFieldNumber;

	for (int i = 0; i < message.field_count(); ++i)
	{
		const FieldDescriptor &field(*message.field(i));
		map<std::string,std::string> variables;
		variables["name"] = GetConflictFreeFieldName(field,fieldNameCollisionSet,fieldParentDeque);
		variables["realName"]         = ToLowerCaseUnderscoreSeparated(field.name());
		variables["fieldNumber"]      = SimpleItoa(field.number()+myStartFieldNumber);
		variables["fieldExtension"]   = GetFieldOptionsAsString(printer,field);
		//For Enum / Simple Type, for complex types override with qualified type names
		variables["typeName"]      = ProtoDataType(field);
		variables["fieldOption"]      ="$$$$$ IMPOSSIBLE_ERROR $$$$$";
		if(field.is_repeated())
			variables["fieldOption"]      ="repeated";               
		if(field.is_required())
			variables["fieldOption"]="required";
		if(field.is_optional())
			variables["fieldOption"]="optional";

		if(field.type()==FieldDescriptor::TYPE_MESSAGE || field.type()==FieldDescriptor::TYPE_GROUP)
		{
			//Get the message descriptor and check if this is in msg db or not
			const Descriptor & newMessage(*field.message_type());
			//Find the type name
			if(PackageName(newMessage)==file.package())
			{
				variables["typeName"] = UnqualifiedClassOrEnumOrFieldName(newMessage);
			}
			else
			{
				variables["typeName"]=QualifiedJavaClassOrEnumName(newMessage);
			}

			if(noExpandMsgDbSet.end() == noExpandMsgDbSet.find(UnqualifiedClassOrEnumOrFieldName(newMessage)))
			{
				//This sub-message is not in db, which means we will expad this inline
				printer.Print(variables,"//Start `typeName` `realName`\n");
				printer.Indent();
				
				fieldParentDeque.push_back(variables["realName"]);
				PrintMessage(printer,file, newMessage, fieldNameCollisionSet, fieldParentDeque, childStartFieldNumber+=100);
				fieldParentDeque.pop_back();
				
				printer.Outdent();
				printer.Print(variables,"//End `typeName` `realName`\n");
			}
			else
			{
				//Message being part of MsgDB means this message need not be expanded inleine
				//Just print it
				printer.Print(variables,"`fieldOption` `typeName` `name`= `fieldNumber``fieldExtension`;\n");
			}
		}
		else
		{
			//This is a simple type or Enum type:
			if(variables["typeName"]=="enum")
			{
				variables["enumName"]=ClassName(*field.enum_type());
				printer.Print(variables,"`fieldOption` `enumName` `name`= `fieldNumber``fieldExtension`;\n");
			}
			else
			{
				printer.Print(variables,"`fieldOption` `typeName` `name` = `fieldNumber``fieldExtension`;\n");
			}
		}
	}
}

void FlattenedModelGen::PrintEnumType(io::Printer &printer,const EnumDescriptor & enummessage) const
{
    printer.Print("enum `name` {\n\n","name",enummessage.name());
    printer.Indent();
    for (int i = 0; i < enummessage.value_count(); ++i) 
	{   
         const EnumValueDescriptor & enumvalue(*enummessage.value(i));    
         printer.Print("    `name`=`fieldnumber`;\n","name",enumvalue.name(),"fieldnumber",SimpleItoa(enumvalue.number()));
    }
	printer.Outdent();
	printer.Print("\n}\n");
}

std::string FlattenedModelGen::GetFieldDefaultValueOptionString(const FieldDescriptor & field)const
{
	std::string retString = "";
	if(field.has_default_value())
	{
		retString = "default = ";
		switch (field.type())
		{
			case FieldDescriptor::TYPE_INT32:
				retString += SimpleItoa(field.default_value_int32());
				break;
			case FieldDescriptor::TYPE_INT64:
				retString += SimpleItoa(field.default_value_int64());
				break;
			case FieldDescriptor::TYPE_UINT32:
				retString += SimpleItoa(field.default_value_uint32());
				break;
			case FieldDescriptor::TYPE_UINT64:
				retString += SimpleItoa(field.default_value_uint64());
				break;
			case FieldDescriptor::TYPE_FLOAT:
				retString += SimpleFtoa(field.default_value_float());
				break;
			case FieldDescriptor::TYPE_DOUBLE:
				retString += SimpleDtoa(field.default_value_double());
				break;
			case FieldDescriptor::TYPE_BOOL:
				retString += field.default_value_bool() ? "true" : "false";
				break;
			case FieldDescriptor::TYPE_STRING:
				retString += "\"" + CEscape(field.default_value_string()) + "\"";
				break;
			case FieldDescriptor::TYPE_BYTES:
				retString += CEscape(field.default_value_string());
				break;
			case FieldDescriptor::TYPE_ENUM:
				retString += QualifiedCppClassOrEnumName(*field.enum_type()) + "::" + field.default_value_enum()->name();
				break;
			default:
				throw;//Unsupported Type
		}
	}
	return retString;
}


std::string FlattenedModelGen::GetFieldOptionsAsString(io::Printer &printer, const FieldDescriptor & field) const
{
	std::string strRetFieldOptionsString = "[";
	size_t initRetFieldOptionsStringLen = strRetFieldOptionsString.length();

	//Set Default Value option if Any:
	strRetFieldOptionsString += GetFieldDefaultValueOptionString(field);

	//Check if any native field options are set, then write them
	const FieldOptions &fieldOptions = field.options();
	if(fieldOptions.has_ctype())
	{
		bool ctype = fieldOptions.ctype();
		std::string strCtype = ctype?"true":"false";
		std::string strPrefix = strRetFieldOptionsString.length()!=initRetFieldOptionsStringLen?", ":" ";
		strRetFieldOptionsString += strPrefix + "ctype = " + strCtype;
	}
	if(fieldOptions.has_packed())
	{
		bool packed = fieldOptions.packed();
		std::string strPacked = packed?"true":"false";
		std::string strPrefix = strRetFieldOptionsString.length()!=initRetFieldOptionsStringLen?", ":" ";
		strRetFieldOptionsString += strPrefix + "packed = " + strPacked;
	}
	if(fieldOptions.has_deprecated())
	{
		bool deprecated = fieldOptions.deprecated();
		std::string strDeprecated = deprecated?"true":"false";
		std::string strPrefix = strRetFieldOptionsString.length()!=initRetFieldOptionsStringLen?", ":" ";
		strRetFieldOptionsString += strPrefix + "deprecated = " + strDeprecated;
	}
	if(fieldOptions.has_experimental_map_key())
	{
		std::string strExperimentalMapKey = fieldOptions.experimental_map_key();
		std::string strPrefix = strRetFieldOptionsString.length()!=initRetFieldOptionsStringLen?", ":" ";
		strRetFieldOptionsString += strPrefix + "experimental_map_key = " + "\"" + strExperimentalMapKey + "\"";
	}

	//Now Deal with uninterpreted options
	for (int i = 0; i < fieldOptions.uninterpreted_option_size(); i++)
	{
		const UninterpretedOption & uninterpretedOption = fieldOptions.uninterpreted_option(i);
		if(0 != uninterpretedOption.name_size())
		{
			std::string strUninterpretedOptionName = uninterpretedOption.name(0).name_part();
			//Only std::string value based options supported at this point
			std::string strUninterpretedOptionValue = uninterpretedOption.string_value();
			if(0 != strUninterpretedOptionValue.length())
			{
				std::string strPrefix = strRetFieldOptionsString.length()!=initRetFieldOptionsStringLen?", ":" ";
				strRetFieldOptionsString += strPrefix + strUninterpretedOptionName + " = \"" + strUninterpretedOptionValue + "\"";
			}
		}
	}
	
	//Now Check if any extension field options are there, then write them
	std::map<std::string, std::set<std::string>* >::const_iterator itr = extensionStore.find("FieldOptions");
	if(extensionStore.end() != itr)
	{
		std::set<std::string>* ptrFieldOptionSet = itr->second;
		for (std::set<std::string>::const_iterator citr = ptrFieldOptionSet->begin();
			 citr != ptrFieldOptionSet->end(); citr++)
	   {
		   std::string strExtensionOptionName = *citr;
		   const FieldDescriptor * extensionFieldDescriptor = fieldOptions.GetReflection()->FindKnownExtensionByName(strExtensionOptionName);
		   //We only support std::string type extensions at this point
		   const std::string strExtensionOptionValue = fieldOptions.GetReflection()->GetString(fieldOptions,extensionFieldDescriptor);
		   if(0 != strExtensionOptionValue.length())
		   {
			   std::string strPrefix = strRetFieldOptionsString.length()!=initRetFieldOptionsStringLen?", ":" ";
			   strRetFieldOptionsString += strPrefix + "(" + strExtensionOptionName + ") = \"" + strExtensionOptionValue + "\"";
		   }
	   }
	}

	strRetFieldOptionsString = strRetFieldOptionsString.length()!=initRetFieldOptionsStringLen? strRetFieldOptionsString+"]":"";
	return strRetFieldOptionsString;
}

void FlattenedModelGen::PrintMessageOptions(io::Printer &printer, const Descriptor & message) const
{
	//Check if any native message options are set, then write them
	const MessageOptions &messageOptions = message.options();
	if(messageOptions.has_message_set_wire_format())
	{
		bool messageSetWireFormat = messageOptions.message_set_wire_format();
		std::string strMessageSetWireFormat = messageSetWireFormat?"true":"false";
		printer.Print("option message_set_wire_format = `strMessageSetWireFormat`;\n", "strMessageSetWireFormat", strMessageSetWireFormat);
	}
	if(messageOptions.has_no_standard_descriptor_accessor())
	{
		bool noStandardDescriptorAccessor = messageOptions.no_standard_descriptor_accessor();
		std::string strNoStandardDescriptorAccessor = noStandardDescriptorAccessor?"true":"false";
		printer.Print("option no_standard_descriptor_accessor = `strNoStandardDescriptorAccessor`;\n", 
					   "strNoStandardDescriptorAccessor", strNoStandardDescriptorAccessor);
	}

	//Now Deal with uninterpreted options
	for (int i = 0; i < messageOptions.uninterpreted_option_size(); i++)
	{
		const UninterpretedOption & uninterpretedOption = messageOptions.uninterpreted_option(i);
		if(0 != uninterpretedOption.name_size())
		{
			std::string strUninterpretedOptionName = uninterpretedOption.name(0).name_part();
			//Only std::string value based options supported at this point
			std::string strUninterpretedOptionValue = uninterpretedOption.string_value();
			if(0 != strUninterpretedOptionValue.length())
			{
				printer.Print("option `strUninterpretedOptionName` = \"`strUninterpretedOptionValue`\";\n", 
							   "strUninterpretedOptionName", strUninterpretedOptionName,
							   "strUninterpretedOptionValue", strUninterpretedOptionValue);
			}
		}
	}
	
	//Now Check if any extension message options are there, then write them
	std::map<std::string, std::set<std::string>* >::const_iterator itr = extensionStore.find("MessageOptions");
	if(extensionStore.end() != itr)
	{
		std::set<std::string>* ptrMessageOptionSet = itr->second;
		for (std::set<std::string>::const_iterator citr = ptrMessageOptionSet->begin();
			 citr != ptrMessageOptionSet->end(); citr++)
		{
			std::string strExtensionOptionName = *citr;
			const FieldDescriptor * extensionFieldDescriptor = messageOptions.GetReflection()->FindKnownExtensionByName(strExtensionOptionName);
			//We only support std::string type extensions at this point
			const std::string strExtensionOptionValue = messageOptions.GetReflection()->GetString(messageOptions,extensionFieldDescriptor);
			if(0 != strExtensionOptionValue.length())
			{
				printer.Print("option (`strExtensionOptionName`) = \"`strExtensionOptionValue`\";\n", 
							   "strExtensionOptionName", strExtensionOptionName,
							   "strExtensionOptionValue", strExtensionOptionValue);
			}
		}
	}
}

void FlattenedModelGen::PrintFileOptions(io::Printer &printer, const FileDescriptor & file) const
{
	if(0 != file.package().length())
	   printer.Print("package `name`;\n","name",file.package());
	
	//Check if any native file options are set, then write them
	const FileOptions &fileOptions = file.options();
	if(fileOptions.has_java_package())
	{
	   std::string strJavaPackage = fileOptions.java_package();
	   printer.Print("option java_package = \"`strJavaPackage`\";\n", "strJavaPackage", strJavaPackage);
	}
	if(fileOptions.has_java_outer_classname())
	{
		std::string strJavaOuterClassName = fileOptions.java_outer_classname();
		printer.Print("option java_outer_classname = \"`strJavaOuterClassName`\";\n", "strJavaOuterClassName", strJavaOuterClassName);	   
	}
	if(fileOptions.has_java_generate_equals_and_hash())
	{
		bool javaGenerateEqualsAndHash = fileOptions.java_generate_equals_and_hash();
		std::string strJavaGenerateEqualsAndHash = javaGenerateEqualsAndHash?"true":"false";
		printer.Print("option java_generate_equals_and_hash = `strJavaGenerateEqualsAndHash`;\n", 
					   "strJavaGenerateEqualsAndHash", strJavaGenerateEqualsAndHash);
	}
	if(fileOptions.has_optimize_for())
	{
		bool optimizeFor = fileOptions.optimize_for();
		std::string strOptimizeFor = optimizeFor?"true":"false";
		printer.Print("option optimize_for = `strOptimizeFor`;\n", "strOptimizeFor", strOptimizeFor);	   
	}
	if(fileOptions.has_cc_generic_services())
	{
		bool ccGenericServices = fileOptions.cc_generic_services();
		std::string strCcGenericServices = ccGenericServices?"true":"false";
		printer.Print("option cc_generic_services = `strCcGenericServices`;\n", "strCcGenericServices", strCcGenericServices);	   
	}
	
	if(fileOptions.has_java_generic_services())
	{
		bool javaGenericServices = fileOptions.java_generic_services();
		std::string strJavaGenericServices = javaGenericServices?"true":"false";
		printer.Print("option java_generic_services = `strJavaGenericServices`;\n", "strJavaGenericServices", strJavaGenericServices);	   
	}
	if(fileOptions.has_py_generic_services())
	{
		bool pyGenericServices = fileOptions.py_generic_services();
		std::string strPyGenericServices = pyGenericServices?"true":"false";
		printer.Print("option py_generic_services = `strPyGenericServices`;\n", "strPyGenericServices", strPyGenericServices);	   
	}
	if(fileOptions.has_java_multiple_files())
	{
		bool javaMultipleFiles = fileOptions.java_multiple_files();
		std::string strjavaMultipleFiles = javaMultipleFiles?"true":"false";
		printer.Print("option java_multiple_files = `strjavaMultipleFiles`;\n", "strjavaMultipleFiles", strjavaMultipleFiles);	   
	}

	//Now Deal with uninterpreted options
	for (int i = 0; i < fileOptions.uninterpreted_option_size(); i++)
	{
		const UninterpretedOption & uninterpretedOption = fileOptions.uninterpreted_option(i);
		if(0 != uninterpretedOption.name_size())
		{
			std::string strUninterpretedOptionName = uninterpretedOption.name(0).name_part();
			//Only std::string value based options supported at this point
			std::string strUninterpretedOptionValue = uninterpretedOption.string_value();
			if(0 != strUninterpretedOptionValue.length())
			{
				printer.Print("option `strUninterpretedOptionName` = \"`strUninterpretedOptionValue`\";\n", 
							   "strUninterpretedOptionName", strUninterpretedOptionName,
							   "strUninterpretedOptionValue", strUninterpretedOptionValue);
			}
		}
	}
	
	//Now Check if any extension file options are there, then write them
	
	std::map<std::string, std::set<std::string>* >::const_iterator itr = extensionStore.find("FileOptions");
	if(extensionStore.end() != itr)
	{
		std::set<std::string>* ptrfileOptionSet = itr->second;
		for (std::set<std::string>::const_iterator citr = ptrfileOptionSet->begin();
			 citr != ptrfileOptionSet->end(); citr++)
	   {
		   std::string strExtensionOptionName = *citr;
		   const FieldDescriptor * extensionFieldDescriptor = fileOptions.GetReflection()->FindKnownExtensionByName(strExtensionOptionName);
		   //We only support std::string type extensions at this point
		   const std::string strExtensionOptionValue = fileOptions.GetReflection()->GetString(fileOptions,extensionFieldDescriptor);
		   if(0 != strExtensionOptionValue.length())
		   {
			   printer.Print("option (`strExtensionOptionName`) = \"`strExtensionOptionValue`\";\n", 
							   "strExtensionOptionName", strExtensionOptionName,
							   "strExtensionOptionValue", strExtensionOptionValue);
		   }
	   }
	}
	//Add one empty line as seperator
	printer.Print("\n");
}

void FlattenedModelGen::PopulateMessageDependencies(io::Printer &printer,const FileDescriptor & file, const Descriptor & message, 
													   std::set <std::string>& dependencyNameSet,const std::string& strCurrentFile) const
{
	for (int i = 0; i < message.field_count(); ++i)
	{
		const FieldDescriptor &field(*message.field(i));
		if(FieldDescriptor::TYPE_MESSAGE == field.type() || FieldDescriptor::TYPE_GROUP == field.type())
		{
			const Descriptor &newMessage(*field.message_type());
			if(noExpandMsgDbSet.end() == noExpandMsgDbSet.find(UnqualifiedClassOrEnumOrFieldName(newMessage)))
			{
				//This sub-message is not in db, which means we eventually will expad this inline
				//So dependency needs to be found out from within this message
				PopulateMessageDependencies(printer,file,newMessage,dependencyNameSet,strCurrentFile);
			}
			else
			{
				//Message being part of MsgDB means this message need not be expanded inleine
				//Just find dependency for this message and add to dependency map
				std::string dependencyFileNameWithRelativePath = newMessage.file()->name();
				size_t pos = dependencyFileNameWithRelativePath.find_last_of('/');
				std::string dependencyFileName = dependencyFileNameWithRelativePath.substr(pos+1,dependencyFileNameWithRelativePath.length());
				
				//Check dependency is not in the same file as us (no need to resolve then)
				if(strCurrentFile != dependencyFileName)
				{
					//The insert may fail if duplicate insertions tried, this is expected behaviour
					dependencyNameSet.insert(dependencyFileName);
				}
			}
		}
		else if(FieldDescriptor::TYPE_ENUM == field.type())
		{
			std::string dependencyFileNameWithRelativePath = field.enum_type()->file()->name();
			size_t pos = dependencyFileNameWithRelativePath.find_last_of('/');
			std::string dependencyFileName = dependencyFileNameWithRelativePath.substr(pos+1,dependencyFileNameWithRelativePath.length());

			//Check dependency is not in the same file as us (no need to resolve then)
			if(strCurrentFile != dependencyFileName)
			{
				//The insert may fail if duplicate insertions tried, this is expected behaviour
				dependencyNameSet.insert(dependencyFileName);
			}
		}
	}
}


void FlattenedModelGen::PopulateFileDependencies(io::Printer &printer, const FileDescriptor & file,
													 std::set <std::string>& dependencyNameSet) const
{
	//Add current file as available dependency
	std::string strCurrentFile = GetProtoFileNameFromFileDescriptor(file);
	for (int i = 0; i < file.message_type_count(); ++i)
	{
		const Descriptor & message(*file.message_type(i));
		if(noExpandMsgDbSet.end() != noExpandMsgDbSet.find(UnqualifiedClassOrEnumOrFieldName(message)))
		{
			PopulateMessageDependencies(printer,file,message,dependencyNameSet,strCurrentFile);
		}//else not required, we dont want messages falling in else in re-gen protos 
	}
}

void FlattenedModelGen::PrintDependencies(io::Printer &printer, const FileDescriptor & file) const
{
	std::set <std::string> dependencyNameSet;
	//First Print Option Dependency
	// TODO(1): Note, we will need to generalize this logic in future to discover option dependencies
	//Many issues now: Duplicate Import Possible, Missing Dependency Possible, Hard Code Name if change issue possible
	printer.Print("import \"`name`\";\n","name","flux_options.proto");
	//Now descover all dependencies of messages / enums of this file
	PopulateFileDependencies(printer,file,dependencyNameSet);
	//Now we have all message dependencies in place, lets print them
	for (std::set<std::string>::iterator it = dependencyNameSet.begin(); it != dependencyNameSet.end(); it++)
	{
		printer.Print("import \"`name`\";\n","name",*it);
	}
	//Add one empty line as seperator
	printer.Print("\n");
}

void FlattenedModelGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
{
	//Print all Enums in this file, inline expansion does not impact ENUMs
	for (int i = 0; i < file.enum_type_count(); ++i)
	{
	   const EnumDescriptor &enummessage(*file.enum_type(i));
	   PrintEnumType(printer,enummessage);
	}

	//Now we process all messages in this file that are mapped in the msg db
	for (int i = 0; i < file.message_type_count(); ++i)
	{
		const Descriptor & message(*file.message_type(i));
		if(noExpandMsgDbSet.end() != noExpandMsgDbSet.find(UnqualifiedClassOrEnumOrFieldName(message)))
		{
			printer.Print("message	`name` {\n","name",UnqualifiedClassOrEnumOrFieldName(message));
			printer.Indent();
			PrintMessageOptions(printer,message);
			std::set<std::string> fieldNameCollisionSet;

			//Check if this message is part of or is HBM Root, if true "Print `name`Pk if does not exist" in the message
			if(hbmRootStoreSet.end() != hbmRootStoreSet.find(UnqualifiedClassOrEnumOrFieldName(message)))
			{
				int fc = 0;
				for ( ; fc < message.field_count(); ++fc) 
				{
					if(ToLowerCaseUnderscoreSeparated((*message.field(fc)).name()) == (ToLowerCaseUnderscoreSeparated(UnqualifiedClassOrEnumOrFieldName(message)) + "_pk"))
					{
						//(1): TODO: Check and confirm that "FluxFldPk" option is set on field, else throw exception
						break;
					}
					//else not required
				}
				if(message.field_count() == fc)
				{
					//`name`Pk not found, Print it with reserved 1
					printer.Print("optional int64 `name`_pk = 1[(FluxFldPk)= \"TRUE\"];\n","name",ToLowerCaseUnderscoreSeparated(UnqualifiedClassOrEnumOrFieldName(message)));
				}
			}//else not required, this message does not need DB persistance hence no Pk required (we do not check user Pk addition error)
			
			//Note: Field 0-9 of each message - including sub-messages are reserved for admin use 
			//all reserved fields must be added as optional if needed
			
			unsigned int childStartFieldNumber = 10;

			std::deque<std::string> fieldParentDeque;
			fieldParentDeque.push_front("");
			PrintMessage(printer,file,message,fieldNameCollisionSet,fieldParentDeque,childStartFieldNumber);			
			printer.Outdent();
			printer.Print("}\n");
		}
	}
}

bool FlattenedModelGen::IsProtoGenRequired(const FileDescriptor& file) const
{
	bool retStatus = false;
	ifstream ifile("../temp/NoExpandMsgDb.txt");
	if (ifile)
		ReadStdSetFromFile(noExpandMsgDbSet,"../temp/NoExpandMsgDb.txt");

	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor & message(*file.message_type(i));
		if(noExpandMsgDbSet.end() != noExpandMsgDbSet.find(UnqualifiedClassOrEnumOrFieldName(message)))
		{
		   //Even finding one message that is in the NoExpandMsgDb is good enough to indicate proto generation required
		   return true;
		}
	}
	
	//Check if any Enum is defined in the file, then we need to re-gen this proto
	if(0 != file.enum_type_count())
		retStatus = true;
	
	return retStatus;
}


bool FlattenedModelGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	std::string strProtoName=getenv("CURRENT_PROTO")?getenv("CURRENT_PROTO"):"";
	if("" == strProtoName)
		throw "PROTO_FILE_NAME_NOT_FOUND_IN: CURRENT_PROTO ENV_VARIABLE";

	//First check if this file needs to be generated or not:
	if(IsProtoGenRequired(*file))
	{
		scoped_ptr<io::ZeroCopyOutputStream> output(
		output_directory->Open("model/"+strProtoName));

		ifstream iExtensionOptionStoreFile("../temp/ExtensionOptionStore.txt");
		if (iExtensionOptionStoreFile)
		   ReadStdMapFromFile(extensionStore,"../temp/ExtensionOptionStore.txt");

		ifstream iHbmRootStoreFile("../temp/HbmRootStore.txt");
		if (iHbmRootStoreFile)		
			ReadStdSetFromFile(hbmRootStoreSet,"../temp/HbmRootStore.txt");
		
		io::Printer printer(output.get(), '`');
		PrintFileOptions(printer, *file);
		PrintDependencies(printer, *file);
		PrintMessages(printer, *file);
	}
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	FlattenedModelGen generator;
	return PluginMain(argc, argv, &generator);
}

