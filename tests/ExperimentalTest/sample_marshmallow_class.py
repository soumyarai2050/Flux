# standard imports
from dataclasses import dataclass

# #rd party imports
from marshmallow import Schema, fields, post_load


@dataclass(slots=True)
class SampleDC:
    id: int
    name: str
    age: int


class SampleSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    age = fields.Int()

    @post_load
    def make_sample(self, data, **kwargs):
        return SampleDC(**data)


schema = SampleSchema()
sample = schema.load({'id': 1, 'name': 'John', 'age': 2})
print(sample, type(sample))

print(schema.dump(sample))

