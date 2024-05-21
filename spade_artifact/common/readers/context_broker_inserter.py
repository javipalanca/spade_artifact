import json
import aiohttp
import asyncio
from loguru import logger
import spade_artifact

class InserterArtifact(spade_artifact.Artifact):
    def __init__(self, jid, passwd, publisher_jid, orion_ip, project_name, columns_update=[],
                 data_processor=None, json_template=None, json_exceptions=None):
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
        self.presence.set_available()
        await asyncio.sleep(1)
        await self.link(self.publisher_jid, self.artifact_callback)

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

    def artifact_callback(self, artifact, payload):
        logger.info(f"Received: [{artifact}] -> {payload}")
        processed_data = self.data_processor(json.loads(payload))
        for data in processed_data:
            asyncio.create_task(self.payload_queue.put(data))

    async def process_and_send_data(self, payload):
        entity_id = f"urn:ngsi-ld:{payload['type']}:{payload['id']}"
        entity_data = self.build_entity_json(payload)

        if self.columns_update:
            for column in self.columns_update:
                if column in entity_data:
                    await self.update_entity_attribute(entity_id, column, entity_data[column]["value"], entity_data["@context"])
                else:
                    logger.warning(f"Column '{column}' not found in entity data for entity '{entity_id}'.")
        else:
            if await self.entity_exists(entity_id):
                await self.update_all_attributes(entity_id, entity_data, entity_data["@context"])
            else:
                entity_data = self.build_entity_json(payload, clean=False) # si la vamos a crear no debemos limpiar los atributos que no esten presentes para generalizar + la estrucutra
                await self.create_new_entity(entity_data)

    def build_entity_json(self, payload, clean=True):
        """
        Constructs the JSON structure for an Orion entity based on the received payload and a template.

        Args:
            payload: The payload received from the publisher artifact.

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
                    return None  # Eliminar el campo si falta la clave
            else:
                return template

        def clean_result(result, exceptions):
            if isinstance(result, dict):
                keys_to_remove = []
                for k, v in result.items():
                    if isinstance(v, dict):
                        clean_result(v,exceptions)
                        # Verificar excepciones antes de eliminar
                        if k in exceptions:
                            if exceptions[k] not in v:
                                keys_to_remove.append(k)
                        else:
                            if ('value' not in v or v['value'] is None) and ('type' in v and k != 'type' and k != 'id'):
                                keys_to_remove.append(k)
                    elif isinstance(v, list):
                        clean_result(v,exceptions)
                        # Eliminar la lista si está vacía
                        if not v:
                            keys_to_remove.append(k)

                for k in keys_to_remove:
                    del result[k]
            elif isinstance(result, list):
                items_to_remove = []
                for item in result:
                    clean_result(item,exceptions)
                    # Eliminar el elemento de la lista si es un diccionario vacío o None
                    if not item:
                        items_to_remove.append(item)

                for item in items_to_remove:
                    result.remove(item)

        def fill_missing_values(result, exceptions):
            if isinstance(result, dict):
                for k, v in result.items():
                    if isinstance(v, dict):
                        exception_key = exceptions.get(k, 'value')
                        if exception_key not in v:
                            v[exception_key] = 'None'
                        else:
                            if isinstance(v[exception_key], dict):
                                fill_missing_values(v[exception_key], exceptions)
                            else:
                                fill_missing_values(v, exceptions)
                    elif isinstance(v, list):
                        fill_missing_values(v, exceptions)
            elif isinstance(result, list):
                for item in result:
                    fill_missing_values(item, exceptions)

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
    async def entity_exists(self, entity_id):
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/{entity_id}"
            async with session.get(url, headers=self.headers) as response:
                return response.status == 200


    async def create_new_entity(self, entity_data):
        async with aiohttp.ClientSession() as session:
            response = await session.post(self.api_url, headers=self.headers, data=json.dumps(locals()["entity_data"]))
            if response.status == 201:
                logger.info(f"Entity created successfully: {await response.text()}")
            else:
                logger.error(f"Failed to create entity, status code: {response.status}, response: {await response.text()}")

    async def update_entity_attribute(self, entity_id, attribute, value, context):
        url = f"{self.api_url}/{entity_id}/attrs/{attribute}"
        payload = {
            "value": value,
            "@context": context,
        }
        async with aiohttp.ClientSession() as session:
            response = await session.patch(url, headers=self.headers, json=payload)
            if response.status == 204:
                logger.info(f"Entity attribute '{attribute}' updated successfully.")
            else:
                logger.error(f"Failed to update entity attribute '{attribute}', status code: {response.status}, response: {await response.text()}")

    async def update_all_attributes(self, entity_id, entity_data, context):
        async with aiohttp.ClientSession() as session:
            for attribute, value in entity_data.items():
                if attribute in ("id", "type", "@context"):
                    continue
                url = f"{self.api_url}/{entity_id}/attrs/{attribute}"
                if attribute == 'location':
                    payload = {
                        "value": value["coordinates"],
                        "@context": context,
                    }

                else:
                    payload = {
                        "value": value["value"],
                        "@context": context,
                    }
                response = await session.patch(url, headers=self.headers, json=payload)
                if response.status == 204:
                    logger.info(f"Entity attribute '{attribute}' updated successfully.")
                else:
                    logger.error(
                        f"Failed to update entity attribute '{attribute}', status code: {response.status}, response: {await response.text()}")

    async def run(self):
        self.presence.set_available()



        while True:
            payload = await self.payload_queue.get()
            await self.process_and_send_data(payload)

