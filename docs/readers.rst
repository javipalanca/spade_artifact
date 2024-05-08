============
Readers
============





CSV Reader
==========
Description
-----------
The ``CSVReaderArtifact`` is a class derived from ``spade_artifact.Artifact`` for asynchronous reading and publishing of data from CSV files. It reads data row by row and can either publish at regular intervals or based on a time column.

Attributes
----------
- **csv_file (str)**: Path to the CSV file.
- **columns (list[str], optional)**: Specific columns to be read. If ``None``, all columns are read.
- **frequency (int, optional)**: The interval in seconds at which rows are published if no ``time_column`` is specified. Defaults to 1 second.
- **time_column (str, optional)**: Specifies the column with timestamp information for timed publishing.

Methods
-------
- **setup()**:
  Marks the artifact as available on the XMPP server, preparing it for operation.

- **run()**:
  Begins reading the CSV file, publishing each row at the set frequency or based on the timestamps in the ``time_column`` if specified.


Use Example
-----------
This example demonstrates how to integrate the ``CSVReaderArtifact`` with a ``ConsumerAgent`` to listen for and process published data. The configuration involves setting up a ``ConsumerAgent`` that subscribes to the ``CSVReaderArtifact`` and handles incoming data payloads.

Steps:


1. **Configuration**: Load agent and artifact details from a configuration file (`config.json`).

2. **Initialization**: Initialize the ``CSVReaderArtifact`` with connection details and start it.

3. **Agent Setup**: Start the ``ConsumerAgent`` and subscribe it to the ``CSVReaderArtifact``. Define a callback function to handle received data.

4. **Execution**: Run both the artifact and agent concurrently. Data processed by the artifact is published and handled by the agent.



.. warning::
   To execute these examples successfully, you must have your own JID (Jabber Identifier) and an XMPP server configured. Ensure that you update the `config.json` file with your specific configuration parameters before running the examples. This setup is necessary to connect and authenticate with your XMPP server properly.


Example Code
~~~~~~~~~~~~


.. code-block:: python

    import asyncio
    import getpass
    import json
    from loguru import logger
    from spade.agent import Agent
    from spade_artifact import ArtifactMixin
    from spade_artifact.common.readers.csvreader import CSVReaderArtifact

    class ConsumerAgent(ArtifactMixin, Agent):
        def __init__(self, *args, artifact_jid: str = None, **kwargs):
            super().__init__(*args, **kwargs)
            self.artifact_jid = artifact_jid

        def artifact_callback(self, artifact, payload):
            logger.info(f"Received from {artifact}: {payload}")

        async def setup(self):
            await asyncio.sleep(2)
            self.presence.subscribe(self.artifact_jid)
            self.presence.set_available()
            await self.artifacts.focus(self.artifact_jid, self.artifact_callback)
            logger.info("Agent ready and listening to the artifact")

    async def main():
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)

        XMPP_SERVER = config["XMPP_SERVER"]
        artifact_name = config["artifact_name"]
        artifact_jid = f"{artifact_name}@{XMPP_SERVER}"
        artifact_passwd = getpass.getpass(prompt=f"Password for artifact {artifact_name}> ")

        agent_name = config["agent_name"]
        agent_jid = f"{agent_name}@{XMPP_SERVER}"
        agent_passwd = getpass.getpass(prompt=f"Password for Agent {agent_name}> ")

        csv_file_path = config["csv_file_path"]
        columns_to_read = config["columns_to_read"]

        time_column = config.get("time_column", None)
        read_frequency = config.get("read_frequency", 1)

        artifact = CSVReaderArtifact(artifact_jid, artifact_passwd, csv_file_path, columns_to_read, read_frequency, time_column)
        await artifact.start()

        agent = ConsumerAgent(jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid)
        await agent.start()
        await artifact.join()
        await artifact.stop()
        await agent.stop()

        print("Agents and Artifacts have been stopped")

    if __name__ == "__main__":
        asyncio.run(main())


API Reader
==========
Description
-----------
The ``APIReaderArtifact`` asynchronously reads and processes data from an API endpoint. It sends HTTP requests to the specified API URL and processes the response data, supporting customizable HTTP methods, parameters, and headers. The processed data is then published at regular intervals.

Attributes
----------
- **api_url (str)**: The URL of the API endpoint to send requests to.
- **data_processor (Callable)**: A function that processes the data received from the API. It returns a list of messages to be published.
- **http_method (str, optional)**: The HTTP method to use for the request, e.g., 'GET', 'POST'. Defaults to 'GET'.
- **params (dict, optional)**: Parameters to be sent in the query string of the request. Defaults to an empty dictionary.
- **headers (dict, optional)**: HTTP headers to send with the request. Defaults to an empty dictionary.
- **time_request (int, optional)**: Time in minutes to wait for the request data update, converted to seconds.

Methods
-------
- **setup()**:
  Marks the artifact's presence as available on the XMPP server.

- **run()**:
  Initiates sending HTTP requests at regular intervals to the API URL, processes the responses with the ``data_processor`` function, and publishes the processed data.

- **update_url()**:
  An overridable method to update the API URL as needed, tailored to specific application requirements.

Use Example
-----------
This example demonstrates how to configure and use  an extension of the ``APIReaderArtifact``, to periodically fetch and process earthquake data from an API. The artifact is used with a ``EarthquakeAgent`` that subscribes and listens for published data.

Steps:


1. **Configuration**: Load agent, artifact, and API details from a configuration file (`config_earthquake.json`).

2. **Initialization**: Initialize the ``EarthquakeReaderArtifact`` with necessary details including the API URL, data processing function, and operational parameters.

3. **Agent Setup**: Start the ``EarthquakeAgent`` and subscribe it to the ``EarthquakeReaderArtifact``. Define a callback function to handle and log received data.

4. **Execution**: Run both the artifact and agent. The artifact periodically updates its query URL based on the current time, fetches data from the API, processes it, and publishes the results, which the agent then handles.

Example Code
~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    import getpass
    from datetime import datetime, timedelta
    from urllib.parse import urlencode
    import json
    from spade.agent import Agent
    from spade_artifact.common.readers.apireader import APIReaderArtifact
    from spade_artifact import ArtifactMixin
    from loguru import logger

    class EarthquakeReaderArtifact(APIReaderArtifact):
        def __init__(self, jid, passwd, api_url, data_processor=None, http_method='GET', params=None, headers=None,
                     time_request=None):
            super().__init__(jid, passwd, api_url, data_processor, http_method, params, headers, time_request)

        async def update_url(self):
            # This method dynamically updates the API URL based on the current time, setting a time window of the last three minutes.
            # This is crucial for fetching only the most recent earthquake data to avoid redundancy and excessive data retrieval.
            start_time = (datetime.utcnow() - timedelta(minutes=3)).strftime('%Y-%m-%dT%H:%M:%S')
            end_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
            parameters = {
                'format': 'geojson',
                'starttime': start_time,
                'endtime': end_time,
                'minmagnitude': '4'
            }
            self.api_url = f"{self.url_template}?{urlencode(parameters)}"
            print(f"Updated url : {self.api_url}")

    # Earthquake data processor function that parses and formats the received JSON data into readable messages.
    # Each message includes the place, magnitude, and time of the earthquake, which are then published by the artifact.
    async def earthquake_data_processor(data):
        messages = []
        if not data['features']:
            return messages

        for earthquake in data['features']:
            place = earthquake['properties']['place']
            magnitude = earthquake['properties']['mag']
            time = datetime.utcfromtimestamp(earthquake['properties']['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            messages.append(f"Place: {place}, Magnitude: {magnitude}, Time: {time}")
        return messages

    class EarthquakeAgent(ArtifactMixin, Agent):
        def __init__(self, *args, artifact_jid: str = None, **kwargs):
            super().__init__(*args, **kwargs)
            self.artifact_jid = artifact_jid

        def artifact_callback(self, artifact, payload):
            # This method logs the data received from the EarthquakeReaderArtifact.
            # It acts as a simple observer that reacts whenever new data is published by the artifact.
            logger.info(f"Received from {artifact}: {payload}")

        async def setup(self):
            # Sets up the agent, subscribing it to the artifact and marking itself available for receiving published data.
            await asyncio.sleep(2)
            self.presence.subscribe(self.artifact_jid)
            self.presence.set_available()
            await self.artifacts.focus(self.artifact_jid, this.artifact_callback)
            logger.info("Agent ready and listening to the artifact")



    async def main():
        with open('config_earthquake.json', 'r') as config_file:
            config = json.load(config_file)

        XMPP_SERVER = config["XMPP_SERVER"]
        artifact_name = config["artifact_name"]
        artifact_jid = f"{artifact_name}@{XMPP_SERVER}"
        artifact_passwd = getpass.getpass(prompt=f"Password for artifact {artifact_name}> ")

        agent_name = config["agent_name"]
        agent_jid = f"{agent_name}@{XMPP_SERVER}"
        agent_passwd = getpass.getpass(prompt=f"Password for Agent {agent_name}> ")

        api_url = config.get('api_url')
        time_request = config.get('time_request', None)

        artifact = EarthquakeReaderArtifact(
            jid=artifact_jid, passwd=artifact_passwd, api_url=api_url,
            data_processor=earthquake_data_processor, time_request=time_request
        )
        await artifact.start()

        agent = EarthquakeAgent(jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid)
        await agent.start()
        await artifact.join()
        await artifact.stop()
        await agent.stop()

        print("Agents and Artifacts have been stopped")

    if __name__ == "__main__":
        asyncio.run(main())


SQL Reader
==========
Description
-----------
The ``DatabaseQueryArtifact`` executes database queries asynchronously, supporting multiple database types including MySQL, SQLite, and PostgreSQL. It manages the query execution, result processing, and timed re-execution, all performed at regular intervals.

Attributes
----------
- **db_type (str)**: Specifies the database type ('mysql', 'sqlite', 'postgresql').
- **connection_params (dict)**: Contains the parameters needed to establish a database connection. Varies depending on `db_type`.
- **query (str)**: The SQL query to be executed.
- **data_processor (Callable, optional)**: A function to process the results of the query.
- **time_request (int, optional)**: Time in seconds between query executions.

Methods
-------
- **setup()**:
  Prepares the artifact for operation by establishing its presence on the XMPP server.

- **run()**:
  Periodically executes the database query, processes the results, and publishes the data.

- **validate_connection_params()**:
  Checks if all necessary connection parameters are present and valid based on the database type.

- **connect_to_database()**:
  Establishes a connection to the database using the appropriate driver and connection parameters.

- **execute_query()**:
  Executes the stored query and fetches the results using the established database connection.



Use Example
-----------
This example demonstrates configuring and using the ``DatabaseQueryArtifact`` to interact with an in-memory SQLite database. The artifact fetches event data from the database, which is processed and handled by an ``EventsAgent``.

Steps:


1. **Database Setup**: Create an in-memory SQLite database and populate it with sample event data.

2. **Initialization**:  Initialize the ``DatabaseQueryArtifact`` with the necessary database connection parameters and SQL query for fetching data.

3. **Agent Setup**: Start the ``EventsAgent`` and subscribe it to the ``DatabaseQueryArtifact``. Define a callback function to handle and log received data.

4. **Execution**: Run both the artifact and agent. The artifact executes the SQL query, processes the results, and publishes them, which the agent then handles.


Example Code
~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    import getpass
    import json
    import os
    from spade.agent import Agent
    import sqlite3
    from spade_artifact import ArtifactMixin
    from loguru import logger
    from spade_artifact.common.readers.sqlreader import DatabaseQueryArtifact

    def create_in_memory_database():
        """
        Creates an in-memory SQLite database and populates it with sample data.
        This function is crucial for setting up a temporary testing environment where
        database operations can be performed without persistent side effects.
        """
        conn = sqlite3.connect("mydatabase.db")
        cur = conn.cursor()
        cur.execute('''CREATE TABLE events (name TEXT, date TEXT, location TEXT)''')
        sample_data = [
            ('Event 1', '2024-04-15', 'Location A'),
            ('Event 2', '2024-05-20', 'Location B'),
            ('Event 3', '2024-06-25', 'Location C')
        ]
        cur.executemany('INSERT INTO events VALUES (?,?,?)', sample_data)
        conn.commit()
        return conn

    async def events_data_processor(data):
        """
        Processes data fetched from the database. Extracts and formats the last event data for publication.
        This data processor is designed to convert raw database records into a more consumable format for
        further actions or notifications.
        """
        messages = []
        event = data[-1]  # Assume the latest event data is to be processed
        event_name, event_date, event_location = event
        messages.append(f"Event: {event_name}, Date: {event_date}, Location: {event_location}")
        return messages

    # The DatabaseQueryArtifact is used to execute SQL queries within an XMPP environment.
    # This artifact handles the database connection, query execution, and scheduling of operations.
    class EventsAgent(ArtifactMixin, Agent):
        def __init__(self, *args, artifact_jid: str = None, **kwargs):
            """
            Initializes the agent that will interact with the DatabaseQueryArtifact.
            This agent listens for the results published by the artifact and handles them
            according to the specified business logic or operational needs.
            """
            super().__init__(*args, **kwargs)
            self.artifact_jid = artifact_jid

        def artifact_callback(self, artifact, payload):
            """
            Callback function to handle the data processed by the artifact.
            Logs each received message from the artifact.
            """
            logger.info(f"Received from {artifact}: {payload}")

        async def setup(self):
            """
            Sets up the agent, subscribing it to the artifact and marking itself available for receiving published data.
            """
            await asyncio.sleep(2)
            self.presence.subscribe(self.artifact_jid)
            self.presence.set_available()
            await self.artifacts.focus(self.artifact_jid, this.artifact_callback)
            logger.info("Agent ready and listening to the artifact")

    async def main():
        in_memory_db = create_in_memory_database()

        with open("config.json", "r") as config_file:
            config = json.load(config_file)

        XMPP_SERVER = config["XMPP_SERVER"]
        artifact_name = config["artifact_name"]
        artifact_jid = f"{artifact_name}@{XMPP_SERVER}"
        artifact_passwd = getpass.getpass(prompt=f"Password for artifact {artifact_name}> ")

        agent_name = config["agent_name"]
        agent_jid = f"{agent_name}@{XMPP_SERVER}"
        agent_passwd = getpass.getpass(prompt=f"Password for Agent {agent_name}> ")

        time_request = config.get('time_request', None)

        artifact = DatabaseQueryArtifact(
            jid=artifact_jid,
            password=artifact_passwd,
            db_type=config["db_type"],
            connection_params=config["connection_params"],
            query=config["query"],
            data_processor=events_data_processor,
            time_request=time_request
        )
        await artifact.start()

        agent = EventsAgent(jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid)
        await agent.start()

        await artifact.join()

        await artifact.stop()
        await agent.stop()

        print("Agents and Artifacts have been stopped")

        cur = in_memory_db.cursor()
        cur.execute("DROP TABLE IF EXISTS events")
        in_memory_db.commit()
        in_memory_db.close()

        os.remove("mydatabase.db")

    if __name__ == "__main__":
        asyncio.run(main())

Mongodb Reader
=============
Description
-----------
The ``MongoDBQueryArtifact`` facilitates executing various MongoDB operations asynchronously, handling operations such as find, insert, update, and delete. It processes the results and allows for performing actions at set intervals, making it ideal for dynamic data handling in MongoDB.

Attributes
----------
- **connection_uri (str)**: MongoDB connection URI used to establish a connection to the database.
- **database_name (str)**: Name of the MongoDB database where operations are performed.
- **collection_name (str)**: Name of the MongoDB collection to operate on.
- **operation (str)**: Specifies the type of operation to perform ('find', 'insert', 'update', 'delete'), determining how the `query` is handled.
- **query (dict)**: MongoDB query or document for the operation. Structure depends on the operation type.
- **data_processor (Callable, optional)**: Function to process the data received from the operation. Defaults to a basic processor that passes data without transformation.
- **time_request (int, optional)**: Interval in seconds to wait before re-executing the operation, allowing for periodic updates.

Methods
-------
- **setup()**:
  Prepares the artifact for operation by setting its presence as available on the XMPP server.

- **run()**:
  Periodically executes the specified MongoDB operation according to `self.time_request`, processes the results, and publishes them.

- **connect_to_database()**:
  Establishes an asynchronous connection to MongoDB, preparing the specified database and collection for operations.

- **execute_operation()**:
  Executes the MongoDB operation defined in `self.operation` and handles the results based on the operation type (find, insert, update, delete).

- **update_query()**:
  An optional method that can be overridden to dynamically update the query before execution, suitable for applications requiring query modifications on-the-fly.


Use Example
-----------
This example demonstrates configuring and using the ``MongoDBQueryArtifact`` to interact with a MongoDB database. The artifact fetches movie data from the database, which is processed and handled by an ``EventsAgent``.

Steps:


1. **Configuration**: Load agent and artifact details from a configuration file (`config.json`), including the MongoDB connection parameters.

2. **Initialization**: Initialize the ``MongoDBQueryArtifact`` with the necessary MongoDB connection URI, database name, collection name, operation type, and query.

3. **Agent Setup**: Start the ``EventsAgent`` and subscribe it to the ``MongoDBQueryArtifact``. Define a callback function to handle and log received data.

4. **Execution**: Run both the artifact and agent. The artifact executes the MongoDB operation, processes the results, and publishes them, which the agent then handles.


Example Code
~~~~~~~~~~~~
The following Python script demonstrates how the ``MongoDBQueryArtifact`` and ``EventsAgent`` are configured and used:

.. code-block:: python

    import asyncio
    import getppass
    from spade.agent import Agent
    from spade_artifact import ArtifactMixin
    from loguru import logger
    from spade_artifact.common.readers.mongodbreader import MongoDBQueryArtifact
    import json

    async def data_processor(data):
        """
        Processes data fetched from the MongoDB database.
        Assumes that data contains at least one movie document and formats the last movie's details into a message.
        """
        last_movie = data[-1]
        title = last_movie.get('title', 'Unknown Title')
        year = last_movie.get('year', 'Unknown Year')
        genres = ', '.join(last_movie.get('genres', ['Unknown Genres']))
        plot = last_movie.get('plot', 'No plot available.')
        messages = [f"Title: {title}\nYear: {year}\nGenres: {genres}\nPlot: {plot}"]
        return messages

    class EventsAgent(ArtifactMixin, Agent):
        def __init__(self, *args, artifact_jid: str = None, **kwargs):
            super().__init__(*args, **kwargs)
            self.artifact_jid = artifact_jid

        def artifact_callback(self, artifact, payload):
            """
            Callback function to handle the data processed by the artifact.
            Logs each received message from the artifact.
            """
            logger.info(f"Received from {artifact}: {payload}")

        async def setup(self):
            """
            Sets up the agent, subscribing it to the artifact and marking itself available for receiving published data.
            """
            await asyncio.sleep(2)
            self.presence.subscribe(self.artifact_jid)
            self.presence.set_available()
            await self.artifacts.focus(self.artifact_jid, this.artifact_callback)
            logger.info("Agent ready and listening to the artifact")

    async def main():
        with open("config.json", "r") as config_file:
            config = json.load(config_file)

        XMPP_SERVER = config["XMPP_SERVER"]
        artifact_name = config["artifact_name"]
        artifact_jid = f"{artifact_name}@{XMPP_SERVER}"
        artifact_passwd = getpass.getpass(prompt=f"Password for artifact {artifact_name}> ")

        agent_name = config["agent_name"]
        agent_jid = f"{agent_name}@{XMPP_SERVER}"
        agent_passwd = getpass.getpass(prompt=f"Password for Agent {agent_name}> ")

        time_request = config.get('time_request', None)

        artifact = MongoDBQueryArtifact(
            connection_uri=config["uri"],
            database_name=config["database_name"],
            collection_name=config["collection_name"],
            operation=config["operation"],
            query=config['query'],
            jid=artifact_jid,
            password=artifact_passwd,
            data_processor=data_processor,
            time_request=time_request
        )
        await artifact.start()

        agent = EventsAgent(jid=agent_jid, password=agent_passwd, artifact_jid=artifact_jid)
        await agent.start()

        await artifact.join()
        await artifact.stop()
        await agent.stop()

        print("Agents and Artifacts have been stopped")

    if __name__ == "__main__":
        asyncio.run(main())

.. warning::
   This example is not functional on its own. To run it, you must have a MongoDB database set up. The code has been tested with a test database on MongoDB Atlas.




