import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from slixmpp import JID

from spade_artifact.common.readers.context_broker_inserter import InserterArtifact
from tests.utils import AsyncContextManagerMock


@pytest.fixture
def artifact():
    jid = "orion@localhost"
    password = "1234"
    publisher_jid = "pubsub@localhost"
    host = "localhost"
    project_name = "orion_tester"

    yield InserterArtifact(jid, password, publisher_jid, host, project_name)


def test_init():
    jid = "orion@localhost"
    password = "1234"
    publisher_jid = "pubsub@localhost"
    host = "localhost"
    project_name = "orion_tester"

    artifact = InserterArtifact(jid, password, publisher_jid, host, project_name)

    assert artifact.jid == JID("orion@localhost")
    assert artifact.password == password
    assert artifact.api_url == "http://localhost:9090/ngsi-ld/v1/entities"
    assert artifact.headers == {
        "Content-Type": "application/ld+json",
        "NGSILD-Tenant": project_name,
    }
    assert artifact.publisher_jid == publisher_jid
    assert artifact.columns_update == []
    assert artifact.data_processor == artifact.default_data_processor
    assert isinstance(artifact.payload_queue, asyncio.Queue)
    assert artifact.json_template == {}
    assert artifact.json_exceptions == {}


async def test_setup(artifact):
    artifact.presence = MagicMock()
    artifact.link = AsyncMock()

    await artifact.setup()

    artifact.presence.set_available.assert_called_once()
    artifact.link.assert_called_once_with(
        "pubsub@localhost", artifact.artifact_callback
    )


@patch("spade_artifact.common.readers.context_broker_inserter.logger")
def test_default_data_processor(mock_logger, artifact):
    data = {
        "payload": "fake",
    }

    result = artifact.default_data_processor(data)
    mock_logger.info.assert_called_once()
    assert result == [data]


@patch("spade_artifact.common.readers.context_broker_inserter.logger")
async def test_artifact_callback(mock_logger, artifact):
    artifact_str = "test_artifact"
    payload = {"payload": "data"}

    artifact.data_processor = MagicMock()
    artifact.data_processor.side_effect = lambda x: [x]
    artifact.artifact_callback(artifact_str, json.dumps(payload))

    mock_logger.info.assert_called_once()
    artifact.data_processor.assert_called_once()
    assert artifact.data_processor.call_args[0][0] == payload


async def test_process_and_send_data(artifact):
    payload = {"type": "fake", "id": "data"}
    artifact.build_entity_json = MagicMock()
    artifact.update_or_create_entity = AsyncMock()
    artifact.update_specific_attributes = AsyncMock()

    await artifact.process_and_send_data(payload)

    artifact.build_entity_json.assert_called_once_with(payload)
    artifact.update_or_create_entity.assert_called_once()
    artifact.update_specific_attributes.assert_not_called()
    args = artifact.update_or_create_entity.call_args[0]
    assert args[0] == "urn:ngsi-ld:fake:data"
    assert args[1] == artifact.build_entity_json.return_value
    assert args[2] == payload


async def test_process_and_send_data_columns_update(artifact):
    payload = {"type": "fake", "id": "data"}
    artifact.columns_update = ["specific", "columns"]
    artifact.build_entity_json = MagicMock()
    artifact.update_or_create_entity = AsyncMock()
    artifact.update_specific_attributes = AsyncMock()

    await artifact.process_and_send_data(payload)

    artifact.build_entity_json.assert_called_once_with(payload)
    artifact.update_or_create_entity.assert_not_called()
    artifact.update_specific_attributes.assert_called_once()
    args = artifact.update_specific_attributes.call_args[0]
    assert args[0] == "urn:ngsi-ld:fake:data"
    assert args[1] == artifact.build_entity_json.return_value


async def test_update_specific_attributes(artifact):
    artifact.columns_update = ["specific", "columns"]
    artifact.update_entity_attribute = AsyncMock()
    mock_entity_data = {
        "@context": MagicMock(),
        "specific": MagicMock(),
        "columns": MagicMock(),
    }

    await artifact.update_specific_attributes("entityid", mock_entity_data)

    assert artifact.update_entity_attribute.call_count == 2
    calls = artifact.update_entity_attribute.call_args_list
    assert calls[0][0][0] == "entityid"
    assert calls[0][0][1] == "specific"
    assert calls[0][0][2] == mock_entity_data["specific"]
    assert calls[0][0][3] == mock_entity_data["@context"]

    assert calls[1][0][0] == "entityid"
    assert calls[1][0][1] == "columns"
    assert calls[1][0][2] == mock_entity_data["columns"]
    assert calls[1][0][3] == mock_entity_data["@context"]


@patch("spade_artifact.common.readers.context_broker_inserter.logger")
async def test_update_specific_attributes_warning(mock_logger, artifact):
    artifact.columns_update = ["badkey"]
    artifact.update_entity_attribute = AsyncMock()
    mock_entity_data = {
        "@context": MagicMock(),
        "specific": MagicMock(),
        "columns": MagicMock(),
    }

    await artifact.update_specific_attributes("entityid", mock_entity_data)

    artifact.update_entity_attribute.assert_not_called()
    mock_logger.warning.assert_called_once()


async def test_update_or_create_entity_exists(artifact):
    artifact.entity_exists = AsyncMock()
    artifact.update_all_attributes = AsyncMock()
    artifact.build_entity_json = MagicMock()
    artifact.create_new_entity = AsyncMock()
    artifact.entity_exists.return_value = True
    mock_entity_data = {
        "@context": MagicMock(),
        "specific": MagicMock(),
        "columns": MagicMock(),
    }
    mock_payload = {"some": "data"}

    await artifact.update_or_create_entity("entityid", mock_entity_data, mock_payload)

    artifact.entity_exists.assert_called_once_with("entityid")
    artifact.update_all_attributes.assert_called_once_with(
        "entityid", mock_entity_data, mock_entity_data["@context"]
    )
    artifact.build_entity_json.assert_not_called()
    artifact.create_new_entity.assert_not_called()


async def test_update_or_create_entity_not_exists(artifact):
    artifact.entity_exists = AsyncMock()
    artifact.update_all_attributes = AsyncMock()
    artifact.build_entity_json = MagicMock()
    artifact.create_new_entity = AsyncMock()
    artifact.entity_exists.return_value = False
    mock_entity_data = {
        "@context": MagicMock(),
        "specific": MagicMock(),
        "columns": MagicMock(),
    }
    mock_entity_data_return = MagicMock()
    artifact.build_entity_json.return_value = mock_entity_data_return
    mock_payload = {"some": "data"}

    await artifact.update_or_create_entity("entityid", mock_entity_data, mock_payload)

    artifact.entity_exists.assert_called_once_with("entityid")
    artifact.update_all_attributes.assert_not_called()
    artifact.build_entity_json.assert_called_once_with(mock_payload, clean=False)
    artifact.create_new_entity.assert_called_once_with(mock_entity_data_return)


async def test_build_entity_json(artifact):
    mock_result = {}
    artifact._replace_placeholders = MagicMock()
    artifact._replace_placeholders.return_value = mock_result
    artifact._clean_result = MagicMock()
    artifact._fill_missing_values = MagicMock()
    artifact.json_template = {
        "@context": MagicMock(),
    }
    mock_payload = {"some": "data"}

    artifact.build_entity_json(mock_payload)

    artifact._replace_placeholders.assert_called_once_with(
        artifact.json_template, mock_payload
    )
    assert "@context" in mock_result
    assert mock_result["@context"] == artifact.json_template["@context"]
    artifact._clean_result.assert_called_once_with(mock_result, {})
    artifact._fill_missing_values.assert_not_called()


async def test_build_entity_json_clean_false(artifact):
    mock_result = {}
    artifact._replace_placeholders = MagicMock()
    artifact._replace_placeholders.return_value = mock_result
    artifact._clean_result = MagicMock()
    artifact._fill_missing_values = MagicMock()
    artifact.json_template = {
        "@context": MagicMock(),
    }
    mock_payload = {"some": "data"}

    artifact.build_entity_json(mock_payload, clean=False)

    artifact._replace_placeholders.assert_called_once_with(
        artifact.json_template, mock_payload
    )
    assert "@context" in mock_result
    assert mock_result["@context"] == artifact.json_template["@context"]
    artifact._clean_result.assert_not_called()
    artifact._fill_missing_values.assert_called_once_with(mock_result, {})


@patch("spade_artifact.common.readers.context_broker_inserter.logger")
async def test_build_entity_json_context_error(mock_logger, artifact):
    mock_result = {}
    artifact._replace_placeholders = MagicMock()
    artifact._replace_placeholders.return_value = mock_result
    artifact._clean_result = MagicMock()
    artifact._fill_missing_values = MagicMock()
    artifact.json_template = {}
    mock_payload = {"some": "data"}

    artifact.build_entity_json(mock_payload)

    artifact._replace_placeholders.assert_called_once_with(
        artifact.json_template, mock_payload
    )
    assert "@context" not in mock_result
    mock_logger.error.assert_called_once()
    artifact._clean_result.assert_called_once_with(mock_result, {})
    artifact._fill_missing_values.assert_not_called()


@patch("spade_artifact.common.readers.context_broker_inserter.aiohttp.ClientSession")
async def test_entity_exists_success(mock_client, artifact):
    mock_response = AsyncMock()
    mock_response.status = 200

    async_mock_response = AsyncContextManagerMock(mock=mock_response)
    mock_session = AsyncContextManagerMock(
        mock=AsyncContextManagerMock(mock=async_mock_response)
    )

    mock_client.return_value = mock_session

    result = await artifact.entity_exists("urn:ngsi-ld:Entity:01")

    assert result is True


@patch("spade_artifact.common.readers.context_broker_inserter.aiohttp.ClientSession")
async def test_entity_exists_false(mock_client, artifact):
    mock_response = AsyncMock()
    mock_response.status = 404

    async_mock_response = AsyncContextManagerMock(mock=mock_response)
    mock_session = AsyncContextManagerMock(
        mock=AsyncContextManagerMock(mock=async_mock_response)
    )

    mock_client.return_value = mock_session

    result = await artifact.entity_exists("urn:ngsi-ld:Entity:01")

    assert result is False


# @patch("spade_artifact.common.readers.context_broker_inserter.aiohttp.ClientSession")
# async def test_entity_exists_failure(mock_client, artifact):
#     async_mock_raise = AsyncContextManagerMock(MagicMock())
#     async_mock_raise.mock.get.return_value = ClientError()
#     # async_mock_raise.get.return_value = ClientError()
#     mock_session = AsyncContextManagerMock(mock=async_mock_raise)
#
#     mock_client.return_value = mock_session
#
#     result = await artifact.entity_exists("urn:ngsi-ld:Entity:01")
#
#     assert result is False


def test_replace_string_placeholder_success(artifact):
    template = "{name}"
    payload = {"name": "Alice"}
    result = artifact._replace_placeholders(template, payload)
    assert result == "Alice"


def test_replace_string_placeholder_missing(artifact):
    template = "{missing_key}"
    payload = {"name": "Alice"}
    result = artifact._replace_placeholders(template, payload)
    assert result is None


def test_static_string_without_placeholder(artifact):
    template = "just_a_normal_string"
    payload = {"name": "Alice"}
    result = artifact._replace_placeholders(template, payload)
    assert result == "just_a_normal_string"


def test_dict_with_id_key(artifact):
    template = {"id": "user_{user_id}"}
    payload = {"user_id": "12345"}
    result = artifact._replace_placeholders(template, payload)
    assert result == {"id": "user_12345"}


def test_dict_recursive_replacement(artifact):
    template = {
        "user": {
            "name": "{name}",
            "age": "{age}",
            "status": "{status}",  # Desaparecerá porque no está en el payload
        }
    }
    payload = {"name": "Bob", "age": 30}
    expected = {"user": {"name": "Bob", "age": 30}}
    result = artifact._replace_placeholders(template, payload)
    assert result == expected


def test_list_replacement_and_filtering(artifact):
    template = ["{item1}", "{missing_item}", "static_value"]
    payload = {"item1": "apple"}
    expected = ["apple", "static_value"]

    result = artifact._replace_placeholders(template, payload)
    assert result == expected


@pytest.mark.parametrize("empty_template", [({"key": "{missing}"}), (["{missing}"])])
def test_empty_structures_return_none(artifact, empty_template):
    result = artifact._replace_placeholders(empty_template, {})
    assert result is None


@pytest.mark.parametrize("primitive_value", [42, True, 3.14, None])
def test_other_data_types(artifact, primitive_value):
    result = artifact._replace_placeholders(primitive_value, {})
    assert result == primitive_value


def test_fill_missing_value_generic(artifact):
    result = {"temperature": {"type": "Property"}}
    artifact._fill_missing_values(result, exceptions={})

    assert result["temperature"]["value"] == "None"


def test_fill_missing_coordinates_for_point(artifact):
    result = {"location": {"type": "Point"}}
    artifact._fill_missing_values(result, exceptions={})

    assert result["location"]["coordinates"] == [0.0, 0.0]


def test_fill_missing_object_for_relationship(artifact):
    result = {"refDevice": {"type": "Relationship"}}
    artifact._fill_missing_values(result, exceptions={})

    assert result["refDevice"]["object"] == "urn:ngsi-ld:Relationship:default"


def test_no_fill_if_key_already_exists(artifact):
    result = {
        "temperature": {"type": "Property", "value": 23.5},
        "location": {"type": "Point", "coordinates": [40.41, -3.70]},
        "refDevice": {"type": "Relationship", "object": "urn:ngsi-ld:Device:01"},
    }
    import copy

    expected = copy.deepcopy(result)

    artifact._fill_missing_values(result, exceptions={})
    assert result == expected


def test_exception_key_override(artifact):
    result = {
        "speed": {
            "type": "Property",
            "custom_value_key": 100,
        },
        "distance": {"type": "Property"},
    }
    exceptions = {"speed": "custom_value_key", "distance": "custom_value_key"}

    artifact._fill_missing_values(result, exceptions)

    assert result["speed"]["custom_value_key"] == 100
    assert "value" not in result["speed"]
    assert result["distance"]["value"] == "None"


def test_recursive_processing_in_lists_and_nested_dicts(artifact):
    result = {
        "metrics": [
            {"humidity": {"type": "Property"}},
            {"sub_group": {"pressure": {"type": "Property"}}},
        ]
    }

    artifact._fill_missing_values(result, exceptions={})

    assert result["metrics"][0]["humidity"]["value"] == "None"
    assert result["metrics"][1]["sub_group"]["pressure"]["value"] == "None"


def test_clean_invalid_property(artifact):
    result = {
        "id": "urn:ngsi-ld:Entity:01",
        "type": "Device",
        "invalid_property": {"type": "Property"},
        "valid_property": {
            "type": "Property",
            "value": 25.0,
        },
    }

    artifact._clean_result(result, exceptions={})

    assert "invalid_property" not in result
    assert "valid_property" in result
    assert result["id"] == "urn:ngsi-ld:Entity:01"


def test_clean_with_exceptions_present(artifact):
    result = {"custom_prop": {"type": "Property", "observedAt": "2026-07-01T12:00:00Z"}}
    exceptions = {"custom_prop": "observedAt"}

    artifact._clean_result(result, exceptions)

    assert "custom_prop" in result


def test_clean_with_exceptions_missing(artifact):
    result = {
        "custom_prop": {
            "type": "Property",
            "value": 123,
        }
    }
    exceptions = {"custom_prop": "observedAt"}

    artifact._clean_result(result, exceptions)

    assert "custom_prop" not in result


def test_clean_empty_lists_and_recursive_removal(artifact):
    result = {"empty_list_key": [], "nested_dict": {"another_empty_list": []}}

    artifact._clean_result(result, exceptions={})

    assert "empty_list_key" not in result


def test_clean_list_of_dicts(artifact):
    result = {
        "items_list": [
            {"type": "Property", "value": "Valid"},
            {"type": "Property"},
        ]
    }

    artifact._clean_result(result, exceptions={})

    assert len(result["items_list"]) == 2
    assert result["items_list"][0]["value"] == "Valid"
    assert result["items_list"][1]["type"] == "Property"


def test_recursive_deep_cleaning(artifact):
    result = {
        "level1": {
            "type": "Property",
            "level2": {"type": "Property"},
        }
    }

    artifact._clean_result(result, exceptions={})

    assert result == {}
