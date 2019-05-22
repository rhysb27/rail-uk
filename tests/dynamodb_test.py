import logging
from unittest import TestCase
from unittest.mock import patch, Mock

from rail_uk import dynamodb
from rail_uk.dtos import Station, HomeStation
from rail_uk.exceptions import DynamoDBError
from helpers import helpers


class TestDynamoDB(TestCase):

    @patch('boto3.resource')
    def test_get_home_station_success(self, mock_boto3):
        mock_table = Mock()
        mock_response = helpers.generate_test_dynamodb_get_response()
        mock_table.get_item.return_value = mock_response
        mock_boto3.return_value.Table.return_value = mock_table

        test_user_id = "existing_user"
        result = dynamodb.get_home_station(test_user_id)

        expected_result = HomeStation(Station('Home Town', 'HTX'), 10)
        self.assertEqual(result, expected_result)

    @patch('boto3.resource')
    def test_get_home_station_no_result(self, mock_boto3):
        mock_table = Mock()
        mock_response = {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            }
        }

        mock_table.get_item.return_value = mock_response
        mock_boto3.return_value.Table.return_value = mock_table

        test_user_id = "garbage"
        result = dynamodb.get_home_station(test_user_id)

        self.assertIsNone(result)

    @patch('boto3.resource')
    @patch('rail_uk.dynamodb.get_home_station')
    def test_set_home_station_success(self, mock_get, mock_boto3):
        mock_table = Mock()
        mock_response = {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            }
        }

        mock_table.put_item.return_value = mock_response
        mock_boto3.return_value.Table.return_value = mock_table
        mock_get.return_value = None

        test_user_id = "new_user"
        test_details = HomeStation(Station('Five Ways', 'FWY'), 10)
        result = dynamodb.set_home_station(test_user_id, test_details)

        self.assertEqual(result, 'set')

    @patch('boto3.resource')
    @patch('rail_uk.dynamodb.get_home_station')
    def test_set_home_station_err(self, mock_get, mock_boto3):
        mock_table = Mock()
        mock_response = {
            'ResponseMetadata': {
                'HTTPStatusCode': 500
            }
        }

        mock_table.put_item.return_value = mock_response
        mock_boto3.return_value.Table.return_value = mock_table
        mock_get.return_value = None

        test_user_id = "existing_user"
        test_details = HomeStation(Station('Five Ways', 'FWY'), 10)

        with self.assertRaises(DynamoDBError) as context:
            dynamodb.set_home_station(test_user_id, test_details)

        self.assertEqual('DynamoDB failed to set home station', str(context.exception))

    @patch('boto3.resource')
    @patch('rail_uk.dynamodb.get_home_station')
    def test_update_home_station_success(self, mock_get, mock_boto3):
        mock_table = Mock()
        mock_response = {
            'Attributes': {
                'station_crs': 'FWY',
                'station_name': 'Five Ways',
                'distance': '10'
            },
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            }
        }

        mock_table.update_item.return_value = mock_response
        mock_boto3.return_value.Table.return_value = mock_table
        mock_get.return_value = HomeStation(Station('University (Birmingham', 'UNI'), 15)

        test_user_id = "existing_user"
        test_details = HomeStation(Station('Five Ways', 'FWY'), 10)
        result = dynamodb.set_home_station(test_user_id, test_details)

        self.assertEqual(result, 'updated')

    @patch('boto3.resource')
    @patch('rail_uk.dynamodb.get_home_station')
    def test_update_home_station_err(self, mock_get, mock_boto3):
        mock_table = Mock()
        mock_response = {}

        mock_table.update_item.return_value = mock_response
        mock_boto3.return_value.Table.return_value = mock_table
        mock_get.return_value = HomeStation(Station('University (Birmingham', 'UNI'), 15)

        test_user_id = "existing_user"
        test_details = HomeStation(Station('Five Ways', 'FWY'), 10)

        with self.assertRaises(DynamoDBError) as context:
            dynamodb.set_home_station(test_user_id, test_details)

        self.assertEqual('DynamoDB failed to update home station', str(context.exception))
