# experiment using Decimal128 type field as timeField in timeseries collection

from pymongo import MongoClient
from bson.decimal128 import Decimal128

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["timeseries_db"]

# Drop the collection if it already exists
db.drop_collection("decimal128_timeseries")

# Create a time series collection
db.create_collection(
    "decimal128_timeseries",
    timeseries={
        "timeField": "timestamp",
        "metaField": "metadata",
        "granularity": "seconds",
    },
)

# Collection handle
collection = db["decimal128_timeseries"]

# Insert sample time series data
data = [
    {
        "timestamp": Decimal128("1696747502.123456"),
        "value": 100,
        "metadata": {"sensor": "temperature", "location": "room1"},
    },
    {
        "timestamp": Decimal128("1696747603.654321"),
        "value": 200,
        "metadata": {"sensor": "temperature", "location": "room2"},
    },
]

result = collection.insert_many(data)
print(f"Inserted documents with IDs: {result.inserted_ids}")