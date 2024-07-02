#!/bin/bash
# This line specifies that the script should be interpreted using bash.

# Setting the variable `venv_dir` to store the name of the virtual environment directory.
venv_dir="../venv"  # Change this to your venv directory name

# Function to compare version numbers
# Defines a function `version_compare` to compare version numbers in the format major.minor.patch.
version_compare() {
    local v1=$1   # Store the first argument as local variable v1
    local v2=$2   # Store the second argument as local variable v2

    if [[ $v1 == $v2 ]]; then   # Compare if v1 is equal to v2
        return 0   # Return 0 (indicating versions are equal)
    fi
}

# Check g++ version
gcc_version=$(g++ --version | grep g++ | awk '{print $4}')
required_gcc_version="13.1.0"  # Adjusted to match with g++ version format
# Retrieves the current g++ version and stores it in `gcc_version`. Sets `required_gcc_version` for comparison.

version_compare $gcc_version $required_gcc_version
gcc_comparison=$?
# Calls `version_compare` with `gcc_version` and `required_gcc_version`, storing the result in `gcc_comparison`.

# Check Python version
python_version=$(python --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+')
required_python_version="3.12"
# Retrieves the current Python version and stores it in `python_version`. Sets `required_python_version` for comparison.

version_compare "$python_version" "$required_python_version"
python_comparison=$?
# Calls `version_compare` with `python_version` and `required_python_version`, storing the result in `python_comparison`.

if [ $gcc_comparison -eq 0 ] && [ $python_comparison -eq 0 ]; then
    if [ -d "$venv_dir" ]; then
        # Activate virtual environment
        source "$venv_dir/bin/activate"
        echo "Virtual environment activated!"
        echo "g++ version: $gcc_version"
        echo "Python version: $python_version"

        # Update LD_LIBRARY_PATH
        unset LD_LIBRARY_PATH
        echo "Updating LD_LIBRARY_PATH"
        export LD_LIBRARY_PATH="/home/$USER/cpp_libs/libs_13/boost/lib:$LD_LIBRARY_PATH"
        export LD_LIBRARY_PATH="/home/$USER/cpp_libs/libs_13/cpp_yaml/lib:$LD_LIBRARY_PATH"
        export LD_LIBRARY_PATH="/home/$USER/cpp_libs/libs_13/mongocxx/lib:$LD_LIBRARY_PATH"
        export LD_LIBRARY_PATH="/home/$USER/cpp_libs/libs_13/protobuf_25.2/lib:$LD_LIBRARY_PATH"
        export LD_LIBRARY_PATH="/home/$USER/cpp_libs/libs_13/quill/lib:$LD_LIBRARY_PATH"

        # Update PATH
        echo "Updating PATH"
        export PATH="/home/$USER/cpp_libs/libs_13/protobuf_25.2/bin:$PATH"
    else
        echo "Virtual environment directory '$venv_dir' not found."
    fi
else
    echo "Either g++ version is not 13 or Python version is not 3.12, LD_LIBRARY_PATH and PATH not updated."
fi
