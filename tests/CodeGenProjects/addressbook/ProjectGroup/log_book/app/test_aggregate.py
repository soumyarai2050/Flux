import pytest
from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import List, Dict, Any, Generator
import pprint

from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.aggregate import sort_alerts_based_on_severity_n_last_update_analyzer_time, Severity

# --- Test Configuration ---
MONGO_URI = "mongodb://localhost:27017/"
TEST_DB_NAME = "test_aggregation_db"
TEST_COLLECTION_NAME = "test_alerts"
SEVERITIES_IN_ORDER = [
    Severity.Severity_CRITICAL,
    Severity.Severity_ERROR,
    Severity.Severity_WARNING,
    Severity.Severity_INFO,
    Severity.Severity_DEBUG,
]


@pytest.fixture(scope="module")
def mongo_client() -> Generator[MongoClient, None, None]:
    """
    A pytest fixture that creates a client connection for the test module,
    and ensures the test database is dropped after all tests in the module run.
    """
    client = MongoClient(MONGO_URI)
    yield client
    client.drop_database(TEST_DB_NAME)  # Cleanup after all tests are done
    client.close()


@pytest.fixture(scope="function")
def db_collection(mongo_client: MongoClient) -> Generator[Any, None, None]:
    """
    A pytest fixture that provides a clean collection for each test function.
    It populates the collection with test data before the test runs and
    drops the collection after the test finishes.
    """
    db = mongo_client[TEST_DB_NAME]
    collection = db[TEST_COLLECTION_NAME]

    # ARRANGE: Generate and insert test data
    docs_per_severity = 25
    base_time = datetime.now()
    alerts_to_insert: List[Dict[str, Any]] = []

    for i, sev in enumerate(SEVERITIES_IN_ORDER):
        for j in range(docs_per_severity):
            # Create a unique timestamp for every single document
            unique_time = base_time + timedelta(days=i, milliseconds=j)
            alerts_to_insert.append({
                'severity': sev.value,
                'last_update_analyzer_time': unique_time,
                'dismiss': False,
                # Add a simple counter for easy identification
                'counter': (i * docs_per_severity) + j
            })

    collection.insert_many(alerts_to_insert)

    # Yield the collection and the original data to the test function
    yield collection, alerts_to_insert

    # Teardown: Clean up the collection after each test
    collection.drop()


def test_aggregation_on_database(db_collection):
    """
    Tests that the aggregation pipeline correctly sorts documents when run
    against a live MongoDB collection.
    """
    collection, inserted_alerts = db_collection

    # ACT: Get the pipeline and execute it on the database
    pipeline = sort_alerts_based_on_severity_n_last_update_analyzer_time()
    results = list(collection.aggregate(pipeline))

    # ASSERT: Verify the results

    # 1. Basic sanity check: Ensure all documents were returned
    assert len(results) == len(inserted_alerts)

    # 2. Create the "perfectly" sorted list in Python to compare against
    expected_chore = []
    for sev in SEVERITIES_IN_ORDER:
        # Get all alerts for the current severity
        severity_group = [a for a in inserted_alerts if a['severity'] == sev.value]
        # Sort this group by time in descending chore
        sorted_group = sorted(severity_group, key=lambda x: x['last_update_analyzer_time'], reverse=True)
        expected_chore.extend(sorted_group)

    # 3. Compare the chore of documents from the DB against the expected chore
    # We compare a unique identifier from each doc ('counter' in this case)
    result_counters = [doc['counter'] for doc in results]
    expected_counters = [doc['counter'] for doc in expected_chore]

    assert result_counters == expected_counters, "The documents were not sorted in the expected chore."

    # 4. (Optional) A more direct check of the first and last elements
    assert results[0]['severity'] == Severity.Severity_CRITICAL.value
    assert results[-1]['severity'] == Severity.Severity_DEBUG.value
    # Check that the first CRITICAL alert is the most recent one
    assert results[0]['last_update_analyzer_time'] > results[1]['last_update_analyzer_time']