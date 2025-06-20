# Useful Sources

## Documentations

* [Protocol Buffers](https://developers.google.com/protocol-buffers)<br>
* [Protocol Buffer Basics: Python](https://developers.google.com/protocol-buffers/docs/pythontutorial)
* [Proto 2](https://developers.google.com/protocol-buffers/docs/proto)
* [Proto 3](https://developers.google.com/protocol-buffers/docs/proto3)
* [pymongo change stream](https://www.mongodb.com/developer/languages/python/python-change-streams/)
* [FastAPI + Pydantic + MongoDB](https://github.com/David-Lor/FastAPI-Pydantic-Mongo_Sample_CRUD_API)
* [Pydantic FastAPI - why we need alias=_id](https://www.mongodb.com/community/forums/t/why-do-we-need-alias-id-in-pydantic-model-of-fastapi/170728/3)
* [Python Shared Memory](https://docs.python.org/3/library/multiprocessing.shared_memory.html)
* [Python Shared Structures Module](https://github.com/fuzziqersoftware/sharedstructures)
* [Python Debugger (Pdb)](https://pypi.org/project/pdb-attach/#:~:text=pdb_attach%20must%20be%20imported%20and,attach%20to%20the%20running%20program.&text=When%20the%20program%20is%20running,listen()%20.)

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

## Setting Up a Single-Node MongoDB Replica Set with Docker

**Step 1: Stop and Remove Any Existing MongoDB Container (If Necessary)**
If you have a plain MongoDB container (not configured as a replica set) or an old replica set container, stop and remove it to avoid conflicts.

*   Find your container ID or name: `docker ps -a`
*   Stop it: `docker stop <your_mongo_container_name_or_id>`
*   Remove it: `docker rm <your_mongo_container_name_or_id>`
*   If you have old volumes you want to clean up (this deletes data): `docker volume rm <volume_name>`

**Step 2: Run a New MongoDB Container as a Single-Node Replica Set**

```bash
docker run -d \
  --name my-mongo-repl \
  -p 27017:27017 \
  -v my-mongo-repl-data:/data/db \
  mongo:latest \
  mongod --replSet rs0 --bind_ip_all
```

**Explanation:**
*   `docker run -d`: Run in detached mode.
*   `--name my-mongo-repl`: A name for your container (e.g., `my-mongo-repl`).
*   `-p 27017:27017`: Maps host port 27017 to the container's MongoDB port 27017.
*   `-v my-mongo-repl-data:/data/db`: Creates and mounts a Docker volume named `my-mongo-repl-data` for persistent data. **Important!**
*   `mongo:latest`: Uses the latest official MongoDB image.
*   `mongod --replSet rs0 --bind_ip_all`:
    *   `--replSet rs0`: Tells `mongod` to be part of a replica set named `rs0`. You can choose a different name if you like, but `rs0` is common for local setups.
    *   `--bind_ip_all`: Makes MongoDB listen on all network interfaces within the container.

**Step 3: Initiate the Single-Node Replica Set**
Connect to the container and initiate the replica set.

*   **Connect to the container's shell:**
    ```bash
    docker exec -it my-mongo-repl mongosh
    ```

*   **Inside `mongosh`, run:**
    ```javascript
    rs.initiate({
      _id: "rs0", // Must match the --replSet name used in docker run
      members: [
        { _id: 0, host: "localhost:27017" } // 'localhost' here refers to the container itself
      ]
    })
    ```
    You should see `{"ok": 1}`. The prompt will change to `rs0:PRIMARY>`.

Your single-node MongoDB replica set is now running and ready!

---

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