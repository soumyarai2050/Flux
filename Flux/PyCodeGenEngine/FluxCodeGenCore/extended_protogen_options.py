import sys
from typing import BinaryIO, List, Dict

import google.protobuf.compiler.plugin_pb2
from protogen import Callable, PyImportPath, default_py_import_func, File, Options

from Flux.PyCodeGenEngine.FluxCodeGenCore.extended_protogen_registry import ExtendedRegistry
from Flux.PyCodeGenEngine.FluxCodeGenCore.extended_protogen_plugin import ExtendedProtogenPlugin


class ExtendedProtogenOptions(Options):
    def __init__(
        self,
        *,
        py_import_func: Callable[[str, str], PyImportPath] = default_py_import_func,
        input: BinaryIO = sys.stdin.buffer,
        output: BinaryIO = sys.stdout.buffer,
    ):
        super().__init__(py_import_func=py_import_func, input=input, output=output)

    def run(self, f: Callable[[ExtendedProtogenPlugin, str, str], None]):
        """Start resolution process and run ``f`` with the :class:`Plugin` containing the resolved classes.

        run waits for protoc to write the CodeGeneratorRequest to
        :attr:`input`, resolves the raw FileDescriptors, Descriptors,
        ServiceDescriptors etc. contained in it to their corresponding
        ``protogen`` classes and creates a new :class:`Plugin` with the resolved
        classes.
        ``f`` is then called with the :class:`Plugin` as argument.
        Once ``f`` returns, :class:`ExtendedProtogenOptions` will collect
        the CodeGeneratorResponse from the :class:`Plugin` that contains information of all
        :class:`GeneratedFile` s that have been created on the plugin. The
        response is written to :attr:`output` for protoc to pick it up. protoc
        writes the generated files to disk.

        Arguments
        ---------
        f : Callable[[Plugin], None]
            Function to run with the Plugin containing the resolved classes.
        """
        req = google.protobuf.compiler.plugin_pb2.CodeGeneratorRequest.FromString(
            self._input.read()
        )

        # Parse parameters. These are given as flags to protoc:
        #
        #   --plugin_opt=key1=value1
        #   --plugin_opt=key2=value2,key3=value3
        #   --plugin_opt=key4,,,
        #   --plugin_opt=key5:novalue5
        #   --plugin_out=key6:./path
        #
        # Multiple in one protoc call are possible. All `plugin_opt`s are joined
        # with a "," in the CodeGeneratorRequest. The equal sign actually has no
        # special meaning, its just a convention.
        #
        # The above would result in a parameter string of
        #
        #   "key1=value1,key2=value2,key3=value3,key4,,,,key5:novalue5,key6"
        #
        # (ignoring the order).
        #
        # Follow the convention of parameters pairs separated by commans in the
        # form {k}={v}. If {k} (without value), write an empty string to the
        # parameter dict. For {k}={v}={v2} write {k} as key and {v}={v2} as
        # value.
        parameter: Dict[str, str] = {}
        for param in req.parameter.split(","):
            if param == "":
                # Ignore empty parameters.
                continue
            splits = param.split("=", 1)  # maximum one split
            if len(splits) == 1:
                k, v = splits[0], ""
            else:
                k, v = splits
            parameter[k] = v

        # Resolve raw proto descriptors to their corresponding protogen classes.
        registry = ExtendedRegistry()
        files_to_generate: List[File] = []
        for proto in req.proto_file:
            generate = proto.name in req.file_to_generate
            file = File(proto, generate, self._py_import_func)
            file._register(registry)
            file._resolve(registry)
            if generate:
                files_to_generate.append(file)

        # Create plugin and run the provided code generation function.
        plugin = ExtendedProtogenPlugin(parameter, files_to_generate, registry)
        f(plugin)

        # Write response.
        resp = plugin._response()

        # @@@ Included insertion points support in extended version
        if not plugin.do_generate_multi_files:
            if (insertion_points_to_content_dict := plugin.insertion_points_to_content_dict) is not None:
                # Adding content at insertion points
                for point, content in insertion_points_to_content_dict.items():
                    resp_f = resp.file.add()
                    resp_f.name = plugin.output_file_name
                    resp_f.insertion_point = point
                    resp_f.content = content
            # else not required: ignore if custom plugin method ``f`` did not assign any
            # value to plugin property insertion_points_to_content_dict
        else:
            insertion_imports_dict = list(plugin.insertion_points_to_content_dict.values())[0]
            # Adding content at insertion points
            for point, content in insertion_imports_dict.items():
                resp_f = resp.file.add()
                resp_f.name = point
                resp_f.insertion_point = point
                resp_f.content = content

        self._output.write(resp.SerializeToString())
