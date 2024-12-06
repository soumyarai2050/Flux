# from fastapi_restful.enums import StrEnum
# from typing import ClassVar
# from dataclasses import dataclass
# from enum import auto
#
# # import cython
# #
# #
# # @cython.cclass
# # class Sample:
# #     name = cython.declare(ClassVar[str], visibility='public')
# #     id = cython.declare(cython.int, visibility='public')
# #
# #     def __init__(self, _id: cython.int):
# #         self.id = _id
#
#
# # class Sample:
# #     name: ClassVar[str]
# #
# #     def __init__(self, _id: int):
# #         self._id = _id
# #
# #     @classmethod
# #     def set_name(cls, name: str) -> None:
# #         cls.name = name
#
# class SampleEnum(StrEnum):
#     Val1 = auto()
#     Val2 = auto()
#     Val3 = auto()
#
# @dataclass
# class Sample:
#     # name: ClassVar[str]
#     _id: int
#     enum_field: SampleEnum
#
#     # @classmethod
#     # def set_name(cls, name: str):
#     #     cls.name = name

def myfunction(x, y=2):
    a = x - y
    return a + x * y

def _helper(a):
    return a + 1

class A:
    def __init__(self, b=0):
        self.a = 3
        self.b = b

    def foo(self, x):
        print(x + _helper(1.0))