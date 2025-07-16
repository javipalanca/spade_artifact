import asyncio

from loguru import logger

import spade_artifact

from motor.motor_asyncio import AsyncIOMotorClient


class MongoDBQueryArtifact(spade_artifact.Artifact):
    """
    An enhanced artifact for executing various MongoDB operations and processing the results.

    This class supports performing a wide range of database operations on MongoDB, such as find,
    insert, update, and delete. It also allows for processing the results and performing actions
    at regular intervals.

    Attributes:
        connection_uri (str): MongoDB connection URI.
        database_name (str): Name of the MongoDB database.
        collection_name (str): Name of the MongoDB collection.
        operation (str): Type of MongoDB operation to be performed. This attribute supports the following operations:
            - 'find': Retrieves documents from the collection that match the criteria specified in `query`. The `query`
             should be a dictionary representing the MongoDB query.
            - 'insert': Inserts a new document into the collection. The `query` should contain the document to be inserted.
            - 'update': Updates documents in the collection that match the criteria. The `query` should be a dictionary
             with 'filter' and 'update' keys, where 'filter' defines the criteria to identify documents to be updated,
             and 'update' specifies the modifications.
            - 'delete': Deletes documents from the collection that match the criteria specified in `query`. The `query`
             should be a dictionary representing the MongoDB deletion criteria.
        query (dict): The MongoDB query or document for operations.
        data_processor (Callable): A function to process the data received from the operation.
        time_request (int, optional): Time in seconds to wait before re-executing the operation.

    Args:
        connection_uri (str): MongoDB connection URI.
        database_name (str): Name of the MongoDB database.
        collection_name (str): Name of the MongoDB collection.
        operation (str): Type of MongoDB operation.
        query (dict): The MongoDB query or document.
        jid (str): JID for the spade artifact.
        password (str): Password for the spade artifact.
        data_processor (Callable, optional): Function to process the operation results. Defaults to None.
        time_request (int, optional): Time in seconds for the operation re-execution interval. Defaults to None.
    """

    def __init__(
        self,
        connection_uri,
        database_name,
        collection_name,
        operation,
        query,
        jid,
        password,
        data_processor=None,
        time_request=None,
    ):
        super().__init__(jid, password)
        self.connection_uri = connection_uri
        self.database_name = database_name
        self.collection_name = collection_name
        self.operation = operation
        self.query = query
        self.data_processor = (
            data_processor
            if data_processor is not None
            else self.default_data_processor
        )
        self.time_request = time_request
        self.client = None
        self.db = None
        self.collection = None

    @staticmethod
    def default_data_processor(data):
        """
        Default data processor function that passes the data through without any transformation.

        Args:
            data: The data received from the API request.

        Returns:
            A list containing the original data.
        """
        logger.info(
            "default data processor started, no data transformation will be done"
        )
        return [data]

    async def update_query(self):
        """
        This method can be overridden to update the API URL as needed.

        By default, this method does nothing. Developers can override it
        to add specific URL update logic for their application.
        """
        pass

    async def connect_to_database(self):
        """
        Asynchronously establishes a connection to the MongoDB database.
        """

        self.client = AsyncIOMotorClient(self.connection_uri)
        self.db = self.client[self.database_name]
        self.collection = self.db[self.collection_name]

    async def execute_operation(self):
        """
        Asynchronously executes the specified MongoDB operation and fetches the results.

        This method supports various operations like find, insert, update, and delete.
        The operation to be performed is determined by `self.operation`.

        Returns:
            The data fetched or affected by executing the specified operation.
        """
        await self.connect_to_database()

        if self.operation == "find":
            cursor = self.collection.find(self.query)
            data = await cursor.to_list(length=None)
            return data
        elif self.operation == "insert":
            result = self.collection.insert_one(self.query)
            return result.inserted_id
        elif self.operation == "update":
            result = self.collection.update_many(
                self.query.get("filter", {}), self.query.get("update", {})
            )
            return result.modified_count
        elif self.operation == "delete":
            result = self.collection.delete_many(self.query)
            return result.deleted_count
        else:
            raise ValueError(f"Unsupported operation: {self.operation}")

    async def run(self):
        """
        Asynchronously and periodically executes the MongoDB query based on `self.time_request`.


        After each iteration, the method waits for `self.time_request` seconds before the next
        execution. When the loop ends, it ensures that the client connection to MongoDB is properly closed to release
        resources.
        """
        continue_query = True

        while continue_query:
            try:
                await self.update_query()
                data = await self.execute_operation()
                processed_data = await self.data_processor(data)
                for message in processed_data:
                    await self.publish(message)

            except Exception as e:
                logger.error(f"An error has been occurred : {e}")

            finally:
                if self.time_request is not None:
                    await asyncio.sleep(self.time_request)
                else:
                    continue_query = False

                if self.client is not None:
                    self.client.close()
