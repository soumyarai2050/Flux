from setuptools import setup, Extension
from Cython.Build import cythonize

# ext_modules = [
#     Extension(
#         "sample_cython_class",
#         sources=["sample_cython_class.pyx"],
#         language="c++",
#         extra_compile_args=["-std=c++17"]
#     )
# ]

ext_modules = [
    Extension(
        "pure_python_cython",
        sources=["sample_pure_python_cython.py"],
        language="c++",
        extra_compile_args=["-std=c++17"]
    )
]

setup(
    ext_modules=cythonize(ext_modules)
)
