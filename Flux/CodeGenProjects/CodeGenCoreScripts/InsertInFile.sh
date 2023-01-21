#!/bin/bash
usage(){
	echo "Invalid Invocation, Usage:"
	echo "$0 \"Command_Name\" \"Input_File_Name\" \"Pattern_String\" \"Insertion_String\"" 
	echo "Where Command_Name cane be:"
	echo "	FIRST_LINE_OF_FILE"
	echo "	LAST_LINE_OF_FILE"
	echo "	BEFORE_LINE_WITH_PATTERN"
	echo "	AFTER_LINE_WITH_PATTERN"
	echo "	REPLACE_LINE_WITH_PATTERN"
	echo "	REPLACE_PATTERN"
	echo "Note: For Commands FIRST_LINE_OF_FILE and LAST_LINE_OF_FILE, Pattern_String is the Insertion_String"
	echo "quitting $0"
	exit 1
}

file_not_exits(){
	local f="$1"
	[[ -f "$f" ]] && return 1 || return 0
}

is_file_exits(){
	local f="$1"
	[[ -f "$f" ]] && return 0 || return 1
}

insert_as_first_line_in_file(){
	# The Command to add input line in file as first line
	local f="$1"
	local t="$2"
	sed -i "1i$t" $f
	return 0
}

insert_as_last_line_in_file(){
	# The Command to add input line in file as last line
	local f="$1"
	local t="$2"
	sed -i "\$a$t" $f
	return 0
}

# Add BEFORE_LINE_WITH_PATTERN, AFTER_LINE_WITH_PATTERN, REPLACE_LINE_WITH_PATTERN, REPLACE_PATTERN
if [ "$1" != "" ] ; then
	#$1 Carries command
	case "$1" in
		FIRST_LINE_OF_FILE|LAST_LINE_OF_FILE|BEFORE_LINE_WITH_PATTERN|AFTER_LINE_WITH_PATTERN|REPLACE_LINE_WITH_PATTERN|REPLACE_PATTERN)
              		# Valid Command supplied, No action needed
			;;
    		*)
              		# Invalid Command 
			echo "$1 does not match any valid Command_Name"
			usage
			;;
	esac
        if [ "$2" != "" ] ; then
		#$2 carries input file name, test it exists
		if ( file_not_exits "$2" )
		then
			echo "Input File $2 does not exist"
			usage
		fi
        	if [ "$3" != "" ] ; then
			#$3 carries pattern string
        		if [ "$4" != "" ] ; then
				#$4 carries insertion string
				case "$1" in
					BEFORE_LINE_WITH_PATTERN)
              					# The Command to add input line in file before the pattern
						sed -n "H;\${x;s/^\n//;s/${3}.*$/${4}\n&/;p;}" $2 > newfile
						#sed -n "H;\${x;s/^\n//;s/${3}.*$/${4}\n&/;p;}" $2 > newfile
						cat newfile > $2
						rm -f newfile
              					;;
    					AFTER_LINE_WITH_PATTERN)
              					# The Command to add input line in file after the pattern
						sed -e"/${3}/a ${4}" $2 > newfile
						cat newfile > $2
						rm -f newfile
						;;
    					REPLACE_LINE_WITH_PATTERN)
              					# The Command to replace line containing pattern with input line
						sed -e "s/${3}/${4}/g" $2 > newfile
						cat newfile > $2
						rm -f newfile
						;;
    					REPLACE_PATTERN)
              					# The Command to just replace the pattern with input line
						sed -i "s/${3}/${4}/g" $2
						;;
				esac
			else
				case "$1" in
        	        		FIRST_LINE_OF_FILE)
						insert_as_first_line_in_file $2 $3
        			                ;;
                			LAST_LINE_OF_FILE)
						insert_as_last_line_in_file $2 $3
	        	        	        ;;
        	        	*)
					# No Insertion String Supplied
					echo "No Insertion String Supplied"
					usage
	                                ;;
        	                esac
        		fi
		else
			case "$1" in
                		FIRST_LINE_OF_FILE|LAST_LINE_OF_FILE)
					# No Insertion String Supplied"
					echo "No Insertion String Supplied"
        		                ;;
                	*)
				# No Pattern to match supplied
				echo "No Pattern to match supplied"
				usage
                	        ;;
		        esac
        	fi
	else
		# No Input File Name Supplied
		echo "No Input File Name Supplied"
		usage
        fi
else
	# No Command Supplied
	echo "No Command Supplied"
	usage
fi
