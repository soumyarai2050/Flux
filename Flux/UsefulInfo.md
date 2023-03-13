# FluxCodeGenEngine

### Google Protoc with Python

## Documentation

* [Protocol Buffers](https://developers.google.com/protocol-buffers)<br>
* [Protocol Buffer Basics: Python](https://developers.google.com/protocol-buffers/docs/pythontutorial)
* [Proto 2](https://developers.google.com/protocol-buffers/docs/proto)
* [Proto 3](https://developers.google.com/protocol-buffers/docs/proto3)
* [pymongo change stream] https://www.mongodb.com/developer/languages/python/python-change-streams/
* [FastAPI + Pydantic + MongoDB] https://github.com/David-Lor/FastAPI-Pydantic-Mongo_Sample_CRUD_API
* [Pydantic FastAPI - why we need alias=_id] https://www.mongodb.com/community/forums/t/why-do-we-need-alias-id-in-pydantic-model-of-fastapi/170728/3

## Tutorials
* [how to implement protobuf in python](https://www.javatpoint.com/how-to-implement-protobuf-in-python)
* [How to Use Google's Protocol Buffers in Python](https://www.freecodecamp.org/news/googles-protocol-buffers-in-python/)

## F&Qs
* [How to define an optional field in protobuf 3](https://stackoverflow.com/questions/42622015/how-to-define-an-optional-field-in-protobuf-3)
* [Why required and optional is removed in Protocol Buffers 3](https://stackoverflow.com/questions/31801257/why-required-and-optional-is-removed-in-protocol-buffers-3)

## Miscellaneous
* [protobuf 2 vs 3 benchmark](https://github.com/thekvs/protobuf-2-vs-3-benchmark)
* [proto2 vs proto3](https://www.hackingnote.com/en/versus/proto2-vs-proto3)

## Useful cmds:

* Linux cmd to make .sh files to unix compatible 
`find . -type d -name "node_modules" -prune -o -name "*.sh" | xargs dos2unix` 

## MongoDb Utils
* Export complete db: 
    ``mongodump --db  SrcDBName``
* Import complete db:
    ``mongorestore --db SrcDBName /path/to/DestDBName``
* Import specific collection: 
    ``mongorestore --collection CollectionName --db DestDBName /path/to/dump/collection/bson/file``
* Export specific collection from remote db:
    ``mongodump --uri <connection_string> --db DBName --collection CollectionName``

## Investigate:
https://studio3t.com/knowledge-base/articles/mongodb-aggregation-framework/
MongoDB $out
db.universities.aggregate([
    { $group: {_id: '$name', totaldocs: { $sum: 1}}},
{ $out: 'aggResults'}])
https://www.mongodb.com/developer/languages/python/beanie-odm-fastapi-cocktails/
result = await Product.find(
    Product.category.name == "Chocolate").aggregate(
    [{"$group": {"_id": "$category.name", "total": {"$avg": "$price"}}}],
    projection_model=OutputItem
).to_list()
db.command('aggregate', 'things', pipeline=pipeline, explain=True)
{'ok': 1.0, 'stages': [...]}
db.collection.update({"_id": ObjectId("55c789499dd5f5f78633da59") // add mongoId to match here},
                     { $set: {"data.key2": "new_value2", "data.new_key3": "new_value3"}}