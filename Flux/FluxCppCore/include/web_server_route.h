#pragma once

#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <regex>

struct Route {
    std::string path;
    std::regex path_pattern;
    std::vector<http::verb> methods;
    std::function<void(http::request<http::string_body>&, http::response<http::string_body>&, const std::smatch& match)> handler;
};