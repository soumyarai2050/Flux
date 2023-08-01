



/**
 * Protocol Buffer Class Standard POCO Compatibility Generator Plugin
 * 
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <FluxFileUtil.h>

class HTMLServiceDescriptionGen: public FluxCodeGenerator 
{
	public:
		void PrintField	(io::Printer &printer, const FieldDescriptor &field, 
						 std::map<std::string, std::string> & fieldAttributeMap) const;
		void ComplexTablePrint    (const Descriptor & messageDescriptor, io::Printer & printer,std::map<std::string, std::string> & messageNameMap) const;
		
		void PrintMessage   (const Descriptor & messageDescriptor, io::Printer & printer,const std::string &strMessageComment) const;
		void PrintMessageExchangeTable	(const FileDescriptor & fileDescriptor, io::Printer & printer) const;
		void PrintMessages	(const FileDescriptor & fileDescriptor, io::Printer & printer) const;
		void PrintFiles (const FileDescriptor* file, io::Printer & printer) const;
		
		HTMLServiceDescriptionGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void HTMLServiceDescriptionGen::PrintField	(io::Printer &printer, const FieldDescriptor &field, 
										 std::map<std::string, std::string> & fieldAttributeMap) const
{
	bool isComplex = false;
	if (FieldDescriptor::TYPE_MESSAGE == field.type()) 
	{
		isComplex = true;
	}

	if (field.is_repeated()) 
	{
		if(isComplex)
		{
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_name`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Number`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\"><a href=\"#`unqualified_type`\">`unqualified_type`</a></td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Option`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_default`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Description`</td>\n");
		}
		else
		{	
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_name`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Number`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`qualified_java_type`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Option`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_default`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Description`</td>\n");
		}
	}
	else 
	{
		// Non repeated field
		if(isComplex)
		{			
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_name`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Number`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\"><a href=\"#`unqualified_type`\">`unqualified_type`</a></td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Option`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_default`</td>\n");
			printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Description`</td>\n");
		}
		else
		{
			//Within simple type we have 4 cases to handle 
			//Strings
			//Enums
			//Rest of It
			//DateTime (Protobuf representation is long)
			/* Default Values - Handeling Strings*/
			switch(field.type())
			{
				case FieldDescriptor::TYPE_STRING:
					{
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_name`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Number`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`qualified_java_type`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Option`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_default`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Description`</td>\n");
					}
					break;
				case FieldDescriptor::TYPE_ENUM:
					{
						
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_name`<div id=\"flip\">show</div>");
						printer.Print(fieldAttributeMap,"<div id=\"panel\"><table>");
						const EnumDescriptor &enummessage (*field.enum_type()) ;
						for (int i = 0; i < enummessage.value_count(); ++i) 
 						{   
       					  const EnumValueDescriptor & enumvalue(*enummessage.value(i));    
       					  printer.Print(" <tr><td class=\"rowSmallData\">\n`name`=`fieldnumber`</td></tr>","name",enumvalue.name(),"fieldnumber",SimpleItoa(enumvalue.number()));
 						}
						printer.Print(fieldAttributeMap,"</table></a>\n</div>\n</td><td class=\"rowData\">`field_Number`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\"><a href=\"#`unqualified_type`\">`unqualified_type`</a></td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Option`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_default`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Description`</td>\n");
					}
					break;
				case FieldDescriptor::TYPE_INT64:
				{
					//Get Default
					//An int64 can or can not be a date time. If its a datetime field, it should have FluxFldValDateTime option set
					std::string strFluxFldTestVal=field.options().GetExtension(FluxFldValDateTime);
					if(0 != strFluxFldTestVal.length())
					{
						//This is a date time field, handle it like that - we should have imported time-support already
					}
					else
					{
						//This is a int64 simple type field handle here
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_name`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Number`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`qualified_java_type`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Option`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_default`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Description`</td>\n");
					}
					break;
				}
				default:
					//All other simple types falll in this case handle here
					{
						//This is any other simple type field, handle here
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_name`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Number`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`qualified_java_type`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Option`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_default`</td>\n");
						printer.Print(fieldAttributeMap,"<td class=\"rowData\">`field_Description`</td>\n");
					}
			}
		}
	}
}

void HTMLServiceDescriptionGen::ComplexTablePrint(const Descriptor &messageDescriptor, io::Printer & printer, std::map<std::string, std::string> & messageNameMap) const
{
	for (int i = 0; i < messageDescriptor.field_count(); ++i) 
	{
		std::map<std::string, std::string> fieldAttributeMap;
		const FieldDescriptor &field ( *messageDescriptor.field(i) );
		fieldAttributeMap["field_name"] = VariableName(field);
		if(field.type() == FieldDescriptor::TYPE_MESSAGE)
		{
			fieldAttributeMap["unqualified_type"] = (*field.message_type()).name();
			if(messageNameMap.find((*field.message_type()).name()) == messageNameMap.end())
			{	
				if (field.is_repeated()) 
				{
					//empty
				}
				else
				{	
					std::string strMessageComment = (*field.message_type()).options().GetExtension(FluxMsgCmnt);
					PrintMessage(*field.message_type(),printer,strMessageComment);
					ComplexTablePrint(*field.message_type(),printer,messageNameMap);
				}
				messageNameMap[(*field.message_type()).name()] = "TRUE";	
			}
		}
	}
}	



void HTMLServiceDescriptionGen::PrintMessage(const Descriptor &messageDescriptor, io::Printer & printer,const std::string &strMessageComment) const
{
	//4.1 For each field in the Message:
	//    - Iterate over all fields we have in this message
	//    - In each iteration Find field's Name, its DataType and populate attribute map (create new attribute map in each iteration)
				printer.Print("<table id=\"`unqualified_name`\">\n","unqualified_name",messageDescriptor.name());
                printer.Print("<thead>\n");
                printer.Print("<tr>\n");
            	printer.Print("<td class=\"messageHeader\">`unqualified_name`</td>\n","unqualified_name",messageDescriptor.name());
				printer.Print("<td></td>\n");
                printer.Print("<td class=\"messageCommentHeader\">`strMessageComment`</td>\n","strMessageComment",strMessageComment);
                printer.Print("</tr>\n");
                printer.Print("</thead>\n");
                printer.Print("<tbody>\n");
	//#########
	printer.Print("<tr id=\"first\">\n");
		printer.Print("<th class=\"tableHeader\">Field</th>\n");
		printer.Print("<th class=\"tableHeader\">Id</th>\n");
		printer.Print("<th class=\"tableHeader\">Type</th>\n");
		printer.Print("<th class=\"tableHeader\">Instance</th>\n");
		printer.Print("<th class=\"tableHeader\">Default</th>\n");
		printer.Print("<th class=\"tableHeader\">Description</th>\n");
	printer.Print("</tr>\n");

	for (int i = 0; i < messageDescriptor.field_count(); ++i) 
	{
		std::map<std::string, std::string> fieldAttributeMap;
		const FieldDescriptor &field ( *messageDescriptor.field(i) );
		fieldAttributeMap["field_Number"]      = SimpleItoa(field.number());
		fieldAttributeMap["field_Description"] = field.options().GetExtension(FluxFldCmnt);	
		fieldAttributeMap["field_default"] =(0!=(DefaultValueAsString(field)).length())?(DefaultValueAsString(field)).c_str():"No Default";
		if (field.is_repeated())
		{
		fieldAttributeMap["field_Option"]  = "repeated";
		}
		else if(field.is_required())
		{
		fieldAttributeMap["field_Option"]  = "required";
		}
		else 
		{
		fieldAttributeMap["field_Option"]  = "optional";
		}
		fieldAttributeMap["field_name"] = VariableName(field);
		//If field is of a complex type or enum type, we need unqualified_type name along with qualified_java_type name for the field 
		if(field.type() == FieldDescriptor::TYPE_MESSAGE)
		{
			//This field is a complex type, it has an un-qualified type name as well
			fieldAttributeMap["unqualified_type"] = (*field.message_type()).name();
		}
		else if(field.type() == FieldDescriptor::TYPE_ENUM)
		{
			//This field is a enum type, it has an un-qualified type name as well
			fieldAttributeMap["unqualified_type"] = (*field.enum_type()).name();
		}
		//Both simple and complex type have Qualified Type Name
		fieldAttributeMap["qualified_java_type"] = QualifiedJavaTypeNameForField(field);
		if(i == messageDescriptor.field_count()-1)
		{	
			printer.Print("<tr id=\"last\">\n");
		}
		else
		{
			printer.Print("<tr>\n");
		}
		
		PrintField(printer, field, fieldAttributeMap);
		printer.Print("</tr>\n");
	}
        printer.Print("</tbody>\n");
        printer.Print("</table>\n");
}




void HTMLServiceDescriptionGen::PrintMessages	(const FileDescriptor & fileDescriptor, io::Printer & printer) const
{
 			
	std::map<std::string, std::string> messageNameMap;
	for (int i = 0; i < fileDescriptor.message_type_count(); ++i) 
	{
		const Descriptor &messageDescriptor(*fileDescriptor.message_type(i));
			
		if(messageNameMap.find(messageDescriptor.name()) == messageNameMap.end())
		{
			std::string strMessageComment = (*fileDescriptor.message_type(i)).options().GetExtension(FluxMsgCmnt);
			PrintMessage(messageDescriptor,printer,strMessageComment);
			messageNameMap[messageDescriptor.name()] = "TRUE";
		}	
	}
	for (int i = 0; i < fileDescriptor.message_type_count(); ++i) 
	{
		const Descriptor &messageDescriptor(*fileDescriptor.message_type(i));
		ComplexTablePrint(messageDescriptor,printer,messageNameMap);
	}		
}



void HTMLServiceDescriptionGen::PrintMessageExchangeTable (const FileDescriptor & fileDescriptor, io::Printer & printer) const
{

	bool first = true;
	for (int i = 0; i < fileDescriptor.message_type_count(); ++i) 
	{
		
		const Descriptor &messageDescriptor(*fileDescriptor.message_type(i));
		std::string strResponse= messageDescriptor.options().GetExtension(FluxMsgRsp);
		if(0!=strResponse.length())
 		{
 			if(first)
 			{
				printer.Print("<tr id=\"first\">\n");
				first = false;
 			}
			else
			{
				printer.Print("<tr>\n");
			}
				printer.Print("<td class=\"rowDataLink\"><a href=\"#`unqualified_name`\">`unqualified_name`</a></td>\n","unqualified_name",messageDescriptor.name());
				printer.Print("<td class=\"rowData\">Synchronous Response</td>\n");
				printer.Print("<td class=\"rowDataLink\"><a href=\"#`syn_responce`\">`syn_responce`</a></td>\n","syn_responce",strResponse);
			printer.Print("</tr>\n");		
		}
	}
}

void HTMLServiceDescriptionGen::PrintFiles (const FileDescriptor* file, io::Printer & printer) const
{
	
	printer.Print("<!DOCTYPE html>\n");
	printer.Print("<html>\n");
	printer.Print("<head>\n");
	
	printer.Print("<script src=\"jquery.js\"></script>\n");
	printer.Print("<script>\n$(document).ready(function(){\n");
	printer.Print("$(\"#flip\").click(function(){\nx=\"show\";\nif ($(\"#flip\").text()==x) {\n$(\"#flip\").text(\"hide\");\n}\nelse {\n$(\"#flip\").text(x);\n}$(\"#panel\").slideToggle(\"slow\");\n");
	printer.Print("  });\n});\n</script>\n");
		
	printer.Print("<style type=\"text/css\">\n");
	printer.Print("#panel,#flip\n{\npadding:5px;\ntext-align:center;\nwidth:50px;\nborder:0;\ncolor:blue;\n}\n");
	printer.Print("#panel\n{\npadding:5px;\ndisplay:none;\ntext-align:left;\ncolor:black;\n}\n");
		
	printer.Print("tbody tr:nth-child(odd) {\n");
	printer.Print("background: rgb(249, 221, 189);\n");
	printer.Print("background: -moz-linear-gradient(-45deg, rgba(249, 221, 189, 1) 0%,\n");
	printer.Print("rgba(252, 231, 206, 1) 35%, rgba(253, 238, 221, 1) 97% );\n");
	printer.Print("}\n");
	
	printer.Print("table {\ntable-layout: fixed;\n");
	printer.Print("padding-top: 20px; border : 0;\n");
	printer.Print("border-collapse: separate;\n");
	printer.Print("border-spacing: 0 5px;\n");
	printer.Print("width: 900px;\n");
	printer.Print("border: 0;\n");
	printer.Print("}\n");
	
	printer.Print("tr#first td {\n");
	printer.Print("border-top: 3px solid #FF920D;\n");
	printer.Print("border-collapse: separate;\n");
	printer.Print("border-spacing: 5px 5px;\n");
	printer.Print("}\n");
	
	printer.Print(".rowDataLink {\n");
	printer.Print("font-family: Times, sans-serif;\n");
	printer.Print("font-weight: bold;\n");
	printer.Print("}\n");

	printer.Print(".rowSmallData{\n");
	printer.Print("font-family: Verdana,sans-serif;\n");
	printer.Print("font-size:12px;\n ");
	printer.Print("}\n");
	
	printer.Print("tbody tr#first th {\n");
	printer.Print("border-top: 3px solid #FF920D;\n");
	printer.Print("border-collapse: separate;\n");
	printer.Print("border-spacing: 5px 5px;\n");
	printer.Print("}\n");
	
	printer.Print("tbody tr#last td {\n");
	printer.Print("border-bottom: 1px solid #FF920D;\n");
	printer.Print("border-collapse: separate;\n");
	printer.Print("border-spacing: 5px 5px;\n");
	printer.Print("}\n");
	
	printer.Print(".messageHeader {\n");
	printer.Print("font-family: Times, sans-serif;\n");
	printer.Print("font-weight: bold;\n");
	printer.Print("}\n");
	
	printer.Print("?.rowData {\n");
	printer.Print("font-family: Verdana, sans-serif;\n");
	printer.Print("}\n");
	
	printer.Print(".tableHeader {\n");
	printer.Print("text-align: left;\n");
	printer.Print("}\n");
	
	printer.Print("a {\n");
	printer.Print("text-decoration: none;\n");
	printer.Print("text-shadow: blue;\n");
	printer.Print("}\n");
	
	printer.Print("a:HOVER {\n");
	printer.Print("text-decoration: underline;\n}\n");

	printer.Print("#flip:HOVER {\n");
	printer.Print("text-decoration: underline;\n");
	printer.Print("}\n");
	printer.Print("</style>\n");
	printer.Print("</head>\n");
	std::string strFileName=GetFileNameFromFileDescriptor(file);
	std::string strFileComment = file->options().GetExtension(FluxFileCmnt);
	printer.Print("<body>\n");
	printer.Print("<label style=\"font-family: Verdana, sans-serif; font-size: 20px; font-weight: bold;\">`strFileName`: </label><label style=\"font-family: Verdana, sans-serif; font-size: 18px;\">`strFileComment`</label>\n", "strFileName", strFileName,"strFileComment",strFileComment);
	printer.Print("<table>\n");
	printer.Print("<thead>\n");
	printer.Print("<tr>\n");
	printer.Print("<td class=\"messageNavigator\" style=\"font-family: Verdana, sans-serif; font-size: 16px; font-weight: bold;\">Message Exchange</td>\n");
	printer.Print("<td></td>\n");
	printer.Print("<td></td>\n");
	printer.Print("</tr>\n");
	printer.Print("</thead>\n");
	printer.Print("<tbody>\n");
	PrintMessageExchangeTable(*file, printer);
	printer.Print("</tbody>\n");
	printer.Print("</table>\n");

			
	PrintMessages(*file, printer);
			


}



bool HTMLServiceDescriptionGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	
	//Step 0.
	std::string strOutputFileName = GetFileNameFromFileDescriptor(file) + ".html";
	//Step 1.
	scoped_ptr<io::ZeroCopyOutputStream> outputFileHandle(output_directory->Open(strOutputFileName));
	//Step 2.	
	io::Printer printer(outputFileHandle.get(), '`');
	//Step 3.
	PrintFiles(file, printer);
	return true;
}

int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	HTMLServiceDescriptionGen generator;
	return PluginMain(argc, argv, &generator);
}
