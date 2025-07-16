import asyncio
import aiohttp
from loguru import logger

import spade_artifact


class APIReaderArtifact(spade_artifact.Artifact):
    """
    An artifact for asynchronously reading and processing data from an API endpoint.

    This artifact sends HTTP requests to a specified API URL and processes the response data. It supports customizable HTTP methods, parameters, and headers. The processed data is then published at regular intervals.

    Attributes:
        api_url (str): The URL of the API endpoint to send requests to.
        data_processor (Callable): A function that processes the data received from the API. It takes the response data as input and returns a list of messages to be published.
        http_method (str, optional): The HTTP method to use for the request (e.g., 'GET', 'POST'). Defaults to 'GET'.
        params (dict, optional): A dictionary of parameters to be sent in the query string of the request. Defaults to an empty dictionary.
        headers (dict, optional): A dictionary of HTTP headers to send with the request. Defaults to an empty dictionary.
        time_request(int, optional) : Time in minutes to wait for the request data update.

    Args:
        jid (str): The JID (Jabber Identifier) of the artifact.
        passwd (str): The password for the artifact to authenticate with the XMPP server.
        api_url (str): The URL of the API endpoint to send requests to.
        data_processor (Callable): The function that will process the data received from the API.
        http_method (str, optional): The HTTP method to use for the request. Defaults to 'GET'.
        params (dict, optional): Parameters to include in the request. Defaults to None, which is converted to an empty dictionary.
        headers (dict, optional): HTTP headers to include in the request. Defaults to None, which is converted to an empty dictionary.
        time_request(int, optional) : Time in minutes to wait for the request data update.
    """

    def __init__(
        self,
        jid,
        passwd,
        api_url,
        data_processor=None,
        http_method="GET",
        params=None,
        headers=None,
        time_request=None,
    ):
        super().__init__(jid, passwd)
        self.api_url = api_url
        self.url_template = api_url
        self.data_processor = (
            data_processor
            if data_processor is not None
            else self.default_data_processor
        )
        self.http_method = http_method
        self.params = params or {}
        self.headers = headers or {}
        self.time_request = (
            time_request * 60 if time_request is not None else time_request
        )

    async def update_url(self):
        """
        This method can be overridden to update the API URL as needed.

        By default, this method does nothing. Developers can override it
        to add specific URL update logic for their application.
        """
        pass

    @staticmethod
    async def default_data_processor(data):
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

    async def setup(self):
        self.presence.set_available()

    async def run(self):
        """
        Starts the artifact's main operation of sending requests to the API and processing the responses.

        This method sends an HTTP request to the specified API URL using the specified method, parameters, and headers. The response is then processed using the `data_processor` function, and the processed data is published at regular intervals.
        """
        self.presence.set_available()

        continue_request = True

        while continue_request:
            await self.update_url()
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    self.http_method,
                    self.api_url,
                    params=self.params,
                    headers=self.headers,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        processed_data = await self.data_processor(data)

                        for message in processed_data:
                            await self.publish(message)
                    else:
                        await self.publish(
                            f"Failed to retrieve data, status code: {response.status}"
                        )

            if self.time_request is None:
                continue_request = False
            else:
                await asyncio.sleep(self.time_request)
