#pragma once
#include <algorithm>

namespace FluxCppCore {
// Literal class type that wraps a constant expression string.
// Uses implicit conversion to allow templates to seemingly
// accept string literals (in double quotes).
// See https://ctrpeach.io/posts/cpp20-string-literal-template-parameters/ for original impl
    template<size_t Size>
    struct StringLiteral {
        constexpr StringLiteral(const char (&str)[Size]) {
            std::copy_n(str, Size, value);
        }
        char value[Size];
    };
}
