import asyncio
from loguru import logger
import spade_artifact
import sqlite3
import pymysql
import psycopg


class DatabaseQueryArtifact(spade_artifact.Artifact):
    """
    An artifact for executing and processing database queries.

    This class supports executing database queries either on SQL or PostgreSQL databases,
    processing the results, and performing actions at regular intervals.

    Attributes:
       db_type (str): The type of the database. This parameter accepts the following values:
            - 'mysql': Indicates that the database is a MySQL database. Requires `pymysql` library.
            - 'sqlite': Indicates that the database is a SQLite database. Uses Python's built-in `sqlite3` library.
            - 'postgresql': Indicates that the database is a PostgreSQL database. Requires `psycopg` library.
        connection_params (dict): Details required to connect to the database. The structure of this dictionary varies based on the `db_type`:
            - For 'mysql' and 'postgresql': This dictionary should include the following keys:
                - 'host': The hostname or IP address of the database server.
                - 'user': The username used to authenticate with the database.
                - 'password': The password used to authenticate with the database.
                - 'database': The name of the database to connect to.
                Additionally, for 'postgresql', the key 'port' can be included to specify the database server port.
            - For 'sqlite': This dictionary needs only one key:
                - 'database': The file path of the SQLite database. If the file does
        query (str): The database query to be executed.
        data_processor (Callable): A function to process the data received from the query.
        time_request (int, optional): Time in seconds to wait before re-executing the query.

    Args:
        db_type (str): The type of the database.
        connection_params (dict): Connection details for the database.
        query (str): The database query.
        data_processor (Callable, optional): Function to process the query results. Defaults to None.
        time_request (int, optional): Time in seconds for the query re-execution interval. Defaults to None.
    """

    def __init__(self, jid, password, db_type, connection_params, query, data_processor=None, time_request=None):
        super().__init__(jid, password)
        self.db_type = db_type
        self.connection_params = connection_params
        self.query = query
        self.data_processor = data_processor if data_processor is not None else self.default_data_processor
        self.time_request = time_request
        self.conn = None
        self.cur = None

    @staticmethod
    def default_data_processor(data):
        """
        Default data processor function that passes the data through without any transformation.

        Args:
            data: The data received from the API request.

        Returns:
            A list containing the original data.
        """
        logger.info('default data processor started, no data transformation will be done')
        return [data]

    async def update_query(self):
        """
        This method can be overridden to update the API URL as needed.

        By default, this method does nothing. Developers can override it
        to add specific URL update logic for their application.
        """
        pass

    def validate_connection_params(self):
        """
        Validates the connection parameters based on the database type.
        Raises:
            ValueError: If required parameters are missing or if there's any issue with the parameters provided.
        """
        if self.db_type == "postgresql":
            required_keys = ['database', 'user', 'host', 'password']
            for key in required_keys:
                if key not in self.connection_params or not self.connection_params[key]:
                    raise ValueError(f"Missing or empty '{key}' in connection parameters for PostgreSQL.")

        elif self.db_type == "mysql":
            required_keys = ['host', 'user', 'password', 'database']
            for key in required_keys:
                if key not in self.connection_params or not self.connection_params[key]:
                    raise ValueError(f"Missing or empty '{key}' in connection parameters for MySQL.")

        elif self.db_type == "sqlite":
            if 'database' not in self.connection_params or not self.connection_params['database']:
                raise ValueError("Missing or empty 'database' in connection parameters for SQLite.")

        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    def prepare_connection_string(self):
        """
        Prepares the database connection string or parameters based on the database type after validating them.
        Returns:
            The connection string for PostgreSQL, a dictionary of parameters for MySQL, or the database filename for SQLite.
        Raises:
            ValueError: If there are issues with the connection parameters or the database type is not supported.
        """
        self.validate_connection_params()

        if self.db_type == "postgresql":
            return self.connection_params
        elif self.db_type == "mysql":
            return self.connection_params
        elif self.db_type == "sqlite":
            return self.connection_params['database']

    async def connect_to_database(self):
        """
        Asynchronously establishes a connection to the database using the appropriate library
        based on `db_type`.

        Raises:
            ValueError: If `db_type` is not supported.
        """
        if self.db_type == "sqlite":
            self.conn = sqlite3.connect(self.prepare_connection_string())
            self.cur = self.conn.cursor()
        elif self.db_type == "postgresql":
            self.conn = psycopg.connect(**self.prepare_connection_string())
            self.cur = self.conn.cursor()
        elif self.db_type == "mysql":
            self.conn = pymysql.connect(**self.prepare_connection_string())
            self.cur = self.conn.cursor()
        else:
            raise ValueError("Unsupported database type")

    async def execute_query(self):
        """
        Asynchronously executes the database query and fetches the results.

        Ensures a database connection is established, then executes the query stored in `self.query`,
        fetches all results, and processes them using `self.data_processor`.

        Returns:
            The data fetched from executing `self.query`.
        """
        await self.connect_to_database()

        self.cur.execute(self.query)
        data = self.cur.fetchall()
        return data

    async def run(self):
        """
        Asynchronously and periodically executes the database query based on `self.time_request`.

        After each iteration, the method waits for `self.time_request` seconds before the next
        execution. When the loop ends, it ensures that the cursor and the database connection
        are properly closed to release resources.
        """
        continue_query = True

        while continue_query:
            try:
                await self.update_query()
                data = await self.execute_query()
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

                if self.cur is not None:
                    self.cur.close()
                if self.conn is not None:
                    await self.conn.close() if hasattr(self.conn, 'close') and asyncio.iscoroutinefunction(
                        self.conn.close) else self.conn.close()
