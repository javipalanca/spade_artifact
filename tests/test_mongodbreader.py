from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from spade_artifact.common.readers.mongodbreader import MongoDBQueryArtifact


@pytest.fixture
def mongoreader():
    connection_uri = "mongodb://localhost:27017"
    database_name = "test"
    collection_name = "test"
    operation = "fake_operation"
    query = {"fake": "dict", "query": "data"}
    jid = "mongo@localhost"
    pwd = "1234"

    yield MongoDBQueryArtifact(
        connection_uri, database_name, collection_name, operation, query, jid, pwd
    )


def test_init():
    connection_uri = "mongodb://localhost:27017"
    database_name = "test"
    collection_name = "test"
    operation = "fake_operation"
    query = {"fake": "dict", "query": "data"}
    jid = "mongo@localhost"
    pwd = "1234"

    mongoreader = MongoDBQueryArtifact(
        connection_uri, database_name, collection_name, operation, query, jid, pwd
    )
    assert mongoreader.connection_uri == connection_uri
    assert mongoreader.database_name == database_name
    assert mongoreader.collection_name == collection_name
    assert mongoreader.operation == operation
    assert mongoreader.query == query
    assert mongoreader.data_processor == mongoreader.default_data_processor
    assert mongoreader.time_request is None
    assert mongoreader.client is None
    assert mongoreader.db is None
    assert mongoreader.collection is None


@patch("spade_artifact.common.readers.mongodbreader.logger")
def test_default_data_processor(mock_log, mongoreader):
    mock_data = MagicMock()

    result = mongoreader.default_data_processor(mock_data)

    assert result == [mock_data]
    mock_log.info.assert_called_once()


@patch("spade_artifact.common.readers.mongodbreader.AsyncIOMotorClient")
async def test_connect_to_database(mock_motor, mongoreader):
    mock_client = MagicMock()
    mock_motor.return_value = mock_client

    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db

    mock_collection = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    await mongoreader.connect_to_database()

    mock_motor.assert_called_once_with(mongoreader.connection_uri)
    assert mongoreader.mongo_client == mock_client
    assert mongoreader.db == mock_db
    assert mongoreader.collection == mock_collection


async def test_execute_operation(mongoreader):
    mongoreader._find_operation = AsyncMock()
    mongoreader._insert_operation = AsyncMock()
    mongoreader._update_operation = AsyncMock()
    mongoreader._delete_operation = AsyncMock()
    mongoreader.connect_to_database = AsyncMock()

    mongoreader.operation = "find"
    result = await mongoreader.execute_operation()
    mongoreader._find_operation.assert_called_once()
    assert result == mongoreader._find_operation.return_value

    mongoreader.operation = "insert"
    result = await mongoreader.execute_operation()
    mongoreader._insert_operation.assert_called_once()
    assert result == mongoreader._insert_operation.return_value

    mongoreader.operation = "update"
    result = await mongoreader.execute_operation()
    mongoreader._update_operation.assert_called_once()
    assert result == mongoreader._update_operation.return_value

    mongoreader.operation = "delete"
    result = await mongoreader.execute_operation()
    mongoreader._delete_operation.assert_called_once()
    assert result == mongoreader._delete_operation.return_value

    mongoreader.operation = "bad_operation"
    with pytest.raises(ValueError):
        await mongoreader.execute_operation()


async def test_find_operation(mongoreader):
    mongoreader.collection = MagicMock()
    mock_cursor = MagicMock()
    mongoreader.collection.find.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock()
    mock_result = MagicMock()
    mock_cursor.to_list.return_value = mock_result

    result = await mongoreader._find_operation()

    mongoreader.collection.find.assert_called_once_with(mongoreader.query)
    mock_cursor.to_list.assert_called_once_with(length=None)
    assert result == mock_result


async def test_insert_operation(mongoreader):
    mongoreader.collection = MagicMock()
    mock_result = MagicMock()
    mongoreader.collection.insert_one.return_value = mock_result

    result = await mongoreader._insert_operation()

    mongoreader.collection.insert_one.assert_called_once_with(mongoreader.query)
    assert result == mock_result.inserted_id


async def test_update_operation(mongoreader):
    mongoreader.collection = MagicMock()
    mock_result = MagicMock()
    mongoreader.collection.update_many.return_value = mock_result

    mock_filter, mock_update = MagicMock(), MagicMock()
    mongoreader.query = {
        "filter": mock_filter,
        "update": mock_update,
    }

    result = await mongoreader._update_operation()

    mongoreader.collection.update_many.assert_called_once_with(mock_filter, mock_update)
    assert result == mock_result.modified_count


async def test_delete_operation(mongoreader):
    mongoreader.collection = MagicMock()
    mock_result = MagicMock()
    mongoreader.collection.delete_many.return_value = mock_result

    result = await mongoreader._delete_operation()

    mongoreader.collection.delete_many.assert_called_once_with(mongoreader.query)
    assert result == mock_result.deleted_count


async def test_run(mongoreader):
    mongoreader.update_query = AsyncMock()
    mongoreader.execute_operation = AsyncMock()
    mongoreader.data_processor = AsyncMock()
    mongoreader.publish = AsyncMock()
    mongoreader.data_processor.return_value = ["fake", "messages"]
    mongoreader.mongo_client = MagicMock()

    await mongoreader.run()

    mongoreader.update_query.assert_called_once()
    mongoreader.execute_operation.assert_called_once()
    mongoreader.data_processor.assert_called_once_with(
        mongoreader.execute_operation.return_value
    )
    assert mongoreader.publish.call_count == 2
    args = mongoreader.publish.call_args_list
    assert args[0][0][0] == "fake"
    assert args[1][0][0] == "messages"
    mongoreader.mongo_client.close.assert_called_once()
