import json
import aiohttp
import asyncio
from loguru import logger
import spade_artifact


class InserterArtifact(spade_artifact.Artifact):
    """
      An artifact for inserting and updating data in an Orion Context Broker.

      This class facilitates communication with an Orion Context Broker instance, allowing
      for the creation and update of entities based on received payloads. It utilizes an
      asynchronous queue to manage incoming data and ensures that data is sent to the context
      broker in a timely manner.

      Attributes:
         api_url (str): The URL of the Orion Context Broker API.
         headers (dict): Headers used for HTTP requests to the Orion Context Broker.
         columns_update (list): A list of columns to update. If empty, all columns are updated.
         data_processor (Callable): Function to process the data received from the artifact.
         json_template (dict): Template for constructing JSON payloads.
         json_exceptions (dict): Exceptions for JSON cleaning rules.

      Args:
          jid (str): Jabber ID for the artifact.
          passwd (str): Password for the artifact's Jabber ID.
          publisher_jid (str): Jabber ID of the publisher artifact.
          orion_ip (str): IP address of the Orion Context Broker.
          project_name (str): Name of the project (used as tenant in headers).
          columns_update (list, optional): List of columns to update. Default is an empty list.
          data_processor (Callable, optional): Function to process data. If None, uses default_data_processor.
          json_template (dict, optional): Template for constructing JSON payloads. Default is an empty dictionary.
          json_exceptions (dict, optional): Exceptions for JSON cleaning rules. Default is an empty dictionary.
      """
    def __init__(self, jid, passwd, publisher_jid, orion_ip, project_name, columns_update=[],
                 data_processor=None, json_template=None, json_exceptions=None):
        """
        Initializes the InserterArtifact object with the given parameters.

        Args:
            jid (str): Jabber ID for the artifact.
            passwd (str): Password for the artifact's Jabber ID.
            publisher_jid (str): Jabber ID of the publisher artifact.
            orion_ip (str): IP address of the Orion Context Broker.
            project_name (str): Name of the project (used as tenant in headers).
            columns_update (list, optional): List of columns to update. Default is an empty list.
            data_processor (callable, optional): Function to process data. If None, uses default_data_processor.
            json_template (dict, optional): Template for constructing JSON payloads. Default is an empty dictionary.
            json_exceptions (dict, optional): Exceptions for JSON cleaning rules. Default is an empty dictionary.
        """
        super().__init__(jid, passwd)

        if json_exceptions is None:
            json_exceptions = {}

        self.api_url = f"http://{orion_ip}:1026/ngsi-ld/v1/entities"
        self.headers = {
            "Content-Type": "application/ld+json",
            "NGSILD-Tenant": project_name
        }
        self.publisher_jid = publisher_jid
        self.columns_update = columns_update
        self.data_processor = data_processor if data_processor is not None else self.default_data_processor
        self.payload_queue = asyncio.Queue()
        self.json_template = json_template or {}
        self.json_exceptions = json_exceptions

    async def setup(self):
        """
        Sets up the InserterArtifact by making it available and linking it to the publisher artifact.

        This method sets the presence to available, waits for a second, and then links the artifact
        to the publisher using the provided publisher_jid. If the linking fails, it logs an error.

        Raises:
            Exception: If linking to the publisher fails.
        """
        self.presence.set_available()
        await asyncio.sleep(1)

        try:
            await self.link(self.publisher_jid, self.artifact_callback)
        except Exception as e:
            logger.error(f"Failed to link with publisher_jid {self.publisher_jid}: {str(e)}")
            raise

    @staticmethod
    def default_data_processor(data: dict) -> list:
        """
        Default data processor function that passes the data through without any transformation.

        This function serves as the default data processor, which simply returns the data encapsulated
        in a list without performing any modifications.

        Args:
            data (dict): The data received from the API request.

        Returns:
            list: A list containing the original data.
        """
        logger.info('default data processor started, no data transformation will be done')
        return [data]

    def artifact_callback(self, artifact: str, payload: str):
        """
        Callback function triggered when data is received from the linked artifact.

        This function processes the received payload using the data processor and
        puts the processed data into the payload queue.

        Args:
            artifact (str): The name or identifier of the artifact sending the data.
            payload (str): The JSON payload received from the artifact.

        Raises:
            json.JSONDecodeError: If the payload is not valid JSON.
        """
        logger.info(f"Received: [{artifact}] -> {payload}")

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON payload: {str(e)}")
            return

        processed_data = self.data_processor(data)
        for data_item in processed_data:
            asyncio.create_task(self.payload_queue.put(data_item))

    async def process_and_send_data(self, payload: dict):
        """
        Processes the given payload and sends the data to the Orion Context Broker.

        This function constructs the entity ID and JSON data, checks if the entity exists,
        and either updates the existing entity's attributes or creates a new entity.

        Args:
            payload (dict): The payload containing data to be sent to the Orion Context Broker.

        Raises:
            KeyError: If 'type' or 'id' keys are missing in the payload.
        """
        try:
            entity_id = f"urn:ngsi-ld:{payload['type']}:{payload['id']}"
        except KeyError as e:
            logger.error(f"Missing key in payload: {str(e)}")
            return

        entity_data = self.build_entity_json(payload)

        if self.columns_update:
            await self.update_specific_attributes(entity_id, entity_data)
        else:
            await self.update_or_create_entity(entity_id, entity_data, payload)

    async def update_specific_attributes(self, entity_id: str, entity_data: dict):
        """
        Updates specific attributes of an existing entity.

        Args:
            entity_id (str): The ID of the entity to update.
            entity_data (dict): The data to update the entity with.
        """
        for column in self.columns_update:
            if column in entity_data:
                attribute_data = entity_data[column]
                await self.update_entity_attribute(entity_id, column, attribute_data, entity_data["@context"])
            else:
                logger.warning(f"Column '{column}' not found in entity data for entity '{entity_id}'.")

    async def update_or_create_entity(self, entity_id: str, entity_data: dict, payload: dict):
        """
        Updates all attributes of an existing entity or creates a new entity if it does not exist.

        Args:
            entity_id (str): The ID of the entity to update or create.
            entity_data (dict): The data to update or create the entity with.
        """
        if await self.entity_exists(entity_id):
            await self.update_all_attributes(entity_id, entity_data, entity_data["@context"])

        else:
            entity_data = self.build_entity_json(payload, clean=False)
            await self.create_new_entity(entity_data)

    def build_entity_json(self, payload, clean=True):
        """
        Constructs the JSON structure for an Orion entity based on the received payload and a template.

        Args:
            payload (dict): The payload received from the publisher artifact.
            clean (bool): Whether to clean the result by removing entries without 'value' or 'type'.

        Returns:
            dict: A dictionary representing the JSON structure of the Orion entity.
        """

        def replace_placeholders(template, payload):
            if isinstance(template, dict):
                result = {}
                for k, v in template.items():
                    if k == "id":
                        result[k] = template[k].format(**payload)
                    else:
                        replaced_value = replace_placeholders(v, payload)
                        if replaced_value is not None:
                            result[k] = replaced_value
                return result if result else None
            elif isinstance(template, list):
                result = [replace_placeholders(item, payload) for item in template]
                result = [item for item in result if item is not None]
                return result if result else None
            elif isinstance(template, str):
                try:
                    key = template.strip("{}")
                    if key in payload:
                        return payload[key]
                    else:
                        return template if "{" not in template and "}" not in template else None
                except KeyError:
                    return None
            else:
                return template

        def fill_missing_values(result, exceptions):
            if isinstance(result, dict):
                for k, v in result.items():
                    if isinstance(v, dict):
                        exception_key = exceptions.get(k, 'value')
                        if exception_key not in v and not any(key in v for key in ['value', 'coordinates', 'object']):
                            if v.get("type") == "Point":
                                v["coordinates"] = [0.0, 0.0]
                            elif v.get("type") == "Relationship":
                                v["object"] = "urn:ngsi-ld:Relationship:default"
                            else:
                                v["value"] = 'None'
                        fill_missing_values(v, exceptions)
                    elif isinstance(v, list):
                        fill_missing_values(v, exceptions)
            elif isinstance(result, list):
                for item in result:
                    fill_missing_values(item, exceptions)

        def clean_result(result, exceptions):
            if isinstance(result, dict):
                keys_to_remove = []
                for k, v in result.items():
                    if isinstance(v, dict):
                        clean_result(v, exceptions)
                        if k in exceptions:
                            if exceptions[k] not in v:
                                keys_to_remove.append(k)
                        else:
                            if (('value' not in v and 'coordinates' not in v and 'object' not in v) and
                                ('type' in v and k != 'type' and k != 'id')):
                                keys_to_remove.append(k)
                    elif isinstance(v, list):
                        clean_result(v, exceptions)
                        if not v:
                            keys_to_remove.append(k)

                for k in keys_to_remove:
                    del result[k]
            elif isinstance(result, list):
                items_to_remove = []
                for item in result:
                    clean_result(item, exceptions)

                    if not item:
                        items_to_remove.append(item)

                for item in items_to_remove:
                    result.remove(item)

        result = replace_placeholders(self.json_template, payload)
        if result is None:
            result = {}

        # Always include the "@context" field
        if "@context" in self.json_template:
            result["@context"] = self.json_template["@context"]
        else:
            logger.error("Context must be provided")

        # Clean the result to remove entries without 'value' or 'type'
        if clean:
            clean_result(result, self.json_exceptions)
        else:
            fill_missing_values(result, self.json_exceptions)

        return result

    async def entity_exists(self, entity_id: str) -> bool:
        """
        Checks if an entity exists in the Orion Context Broker.

        This function sends a GET request to the Orion Context Broker to check if an entity with
        the specified ID exists.

        Args:
            entity_id (str): The ID of the entity to check.

        Returns:
            bool: True if the entity exists, False otherwise.

        Raises:
            Exception: If the HTTP request fails.
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/{entity_id}"
            try:
                async with session.get(url, headers=self.headers) as response:
                    return response.status == 200
            except aiohttp.ClientError as e:
                logger.error(f"HTTP request failed while checking if entity exists: {str(e)}")
                return False

    async def create_new_entity(self, entity_data: dict):
        """
        Creates a new entity in the Orion Context Broker.

        This function sends a POST request to the Orion Context Broker to create a new entity
        with the provided data.

        Args:
            entity_data (dict): The data for the new entity.

        Raises:
            Exception: If the HTTP request fails or the entity creation is unsuccessful.
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, headers=self.headers, json=entity_data) as response:
                    if response.status == 201:
                        logger.info(f"Entity created successfully: {await response.text()}")
                    else:
                        logger.error(
                            f"Failed to create entity, status code: {response.status},"
                            f" response: {await response.text()}")
            except aiohttp.ClientError as e:
                logger.error(f"Failed to create new entity: {str(e)}")

    async def update_entity_attribute(self, entity_id: str, attribute: str, attribute_data: dict, context: any):
        """
        Updates a specific attribute of an existing entity in the Orion Context Broker.

        This function sends a PATCH request to the Orion Context Broker to update a specific attribute
        of an entity with the provided data. If the attribute does not exist, it uses a POST request to add it.

        Args:
            entity_id (str): The ID of the entity to update.
            attribute (str): The attribute of the entity to update.
            attribute_data (dict): The data to update the attribute with.
            context (any): The JSON-LD context to include in the payload.

        Raises:
            Exception: If the HTTP request fails or the attribute update is unsuccessful.
        """
        url_patch = f"{self.api_url}/{entity_id}/attrs/{attribute}"
        url_post = f"{self.api_url}/{entity_id}/attrs"

        # Determine the type of the attribute and construct the payload accordingly
        if attribute == 'location' and isinstance(attribute_data, dict) and "coordinates" in attribute_data:
            payload = {
                "type": "GeoProperty",
                "value": {
                    "type": "Point",
                    "coordinates": attribute_data["coordinates"]
                },
                "@context": context,
            }
        elif isinstance(attribute_data, dict) and "object" in attribute_data:
            payload = {
                "type": "Relationship",
                "object": attribute_data["object"],
                "@context": context,
            }
        else:
            payload = {
                "type": "Property",
                "value": attribute_data.get("value", attribute_data),
                "@context": context,
            }

        async with aiohttp.ClientSession() as session:
            try:
                # Attempt to update the attribute using PATCH
                async with session.patch(url_patch, headers=self.headers, json=payload) as response:
                    if response.status == 204:
                        logger.info(f"Entity attribute '{attribute}' updated successfully.")
                    elif response.status == 207:
                        # If the attribute doesn't exist, add it using POST
                        logger.warning(f"Attribute '{attribute}' does not exist. Adding it using POST.")
                        post_payload = {attribute: payload}
                        post_payload["@context"] = context
                        async with session.post(url_post, headers=self.headers, json=post_payload) as post_response:
                            if post_response.status == 204:
                                logger.info(f"Entity attribute '{attribute}' added successfully.")
                            else:
                                logger.error(
                                    f"Failed to add entity attribute '{attribute}' with POST, status code: {post_response.status},"
                                    f" response: {await post_response.text()}")
                    else:
                        logger.error(
                            f"Failed to update entity attribute '{attribute}' with PATCH, status code: {response.status},"
                            f" response: {await response.text()}")
            except aiohttp.ClientError as e:
                logger.error(f"Failed to update entity attribute '{attribute}': {str(e)}")

    async def update_all_attributes(self, entity_id, entity_data, context):
        """
        Updates all attributes of an existing entity in the Orion Context Broker.

        This function sends a PATCH request to the Orion Context Broker to update each attribute
        of an entity with the provided data. If any attribute does not exist, it uses a POST request to add it.

        Args:
            entity_id (str): The ID of the entity to update.
            entity_data (dict): The data to update the entity with.
            context (any): The JSON-LD context to include in the payload.

        Raises:
            Exception: If the HTTP request fails or the attribute update is unsuccessful.
        """
        async with aiohttp.ClientSession() as session:
            for attribute, value in entity_data.items():
                if attribute in ("id", "type", "@context"):
                    continue
                url_patch = f"{self.api_url}/{entity_id}/attrs/{attribute}"
                url_post = f"{self.api_url}/{entity_id}/attrs"

                if attribute == 'location':
                    payload = {
                        "type": "GeoProperty",
                        "value": {
                            "type": "Point",
                            "coordinates": value["coordinates"]
                        },
                        "@context": context,
                    }
                elif isinstance(value, dict) and "object" in value:
                    payload = {
                        "type": "Relationship",
                        "object": value["object"],
                        "@context": context,
                    }
                else:
                    payload = {
                        "type": "Property",
                        "value": value,
                        "@context": context,
                    }

                response = await session.patch(url_patch, headers=self.headers, json=payload)
                if response.status == 204:
                    logger.info(f"Entity attribute '{attribute}' updated successfully.")
                elif response.status == 404:
                    logger.warning(f"Attribute '{attribute}' does not exist. Adding it using POST.")
                    post_payload = {attribute: payload}
                    post_payload["@context"] = context
                    post_response = await session.post(url_post, headers=self.headers, json=post_payload)
                    if post_response.status == 204:
                        logger.info(f"Entity attribute '{attribute}' added successfully.")
                    else:
                        logger.error(
                            f"Failed to add entity attribute '{attribute}' with POST, status code: {post_response.status},"
                            f" response: {await post_response.text()}")
                else:
                    logger.error(
                        f"Failed to update entity attribute '{attribute}' with PATCH, status code: {response.status},"
                        f" response: {await response.text()}")
    async def run(self):
        """
        Continuously processes and sends data from the payload queue to the Orion Context Broker.

        This function sets the presence to available and enters an infinite loop where it waits
        for data from the payload queue, processes it, and sends it to the Orion Context Broker.

        Raises:
            Exception: If processing or sending data fails.
        """
        self.presence.set_available()

        while True:
            try:
                payload = await self.payload_queue.get()
                await self.process_and_send_data(payload)
            except Exception as e:
                logger.error(f"Error processing and sending data: {str(e)}")
