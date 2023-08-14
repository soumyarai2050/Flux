namespace FluxCppCore {
    class StringUtil {
    public:
        std::string str_tolower(std::string messgage_name)
        {
            std::transform(messgage_name.begin(), messgage_name.end(), messgage_name.begin(), [](unsigned char c){ return std::tolower(c); });
            return messgage_name;
        }

        std::string camel_to_snake(std::string msg_name)
        {

            // Empty String
            std::string result = "";

            // Append first character(in lower case)
            // to result string
            char c = std::tolower(msg_name[0]);
            result+=(char(c));

            // Traverse the string from
            // ist index to last index
            for (int i = 1; i < msg_name.length(); i++) {

                char ch = msg_name[i];

                // Check if the character is upper case
                // then append '_' and such character
                // (in lower case) to result string
                if (std::isupper(ch)) {
                    result = result + '_';
                    result+=char(std::tolower(ch));
                }

                    // If the character is lower case then
                    // add such character into result string
                else {
                    result = result + ch;
                }
            }

            // return the result
            return result;
        }
    };
}