from unittest import TestCase
from unittest.mock import patch, Mock
from datetime import datetime

from rail_uk import data
from rail_uk.dtos import Station, APIParameters
from rail_uk.exceptions import ApplicationError, OpenLDBWSError, TransportAPIError
from helpers import helpers


class TestData(TestCase):

    def setUp(self):
        self.mock_env = helpers.get_test_env()
        self.mock_env.start()

    def tearDown(self):
        self.mock_env.stop()

    @patch('rail_uk.data.make_soap_request')
    @patch('rail_uk.data.parse_departures_soap_response')
    def test_get_next_departures_none(self, mock_parser, mock_request):
        test_params = helpers.generate_test_api_params()

        mock_request.return_value = helpers.MockRestResponse(json_content={})
        mock_parser.return_value = None

        departures = data.get_next_departures(test_params, num_departures=1)
        self.assertIsNone(departures)

    @patch('rail_uk.data.make_soap_request')
    @patch('rail_uk.data.parse_departures_soap_response')
    def test_get_next_departures_single(self, mock_parser, mock_request):
        test_params = helpers.generate_test_api_params()
        example_departure = helpers.generate_departure_details(etd='On time', in_past=False)

        mock_request.return_value = helpers.MockRestResponse(json_content={})
        mock_parser.return_value = [
            example_departure
        ]

        departure = data.get_next_departures(test_params, num_departures=1)
        self.assertTupleEqual(example_departure, departure)

    @patch('rail_uk.data.make_soap_request')
    @patch('rail_uk.data.parse_departures_soap_response')
    def test_get_next_departures_multiple(self, mock_parser, mock_request):
        test_params = helpers.generate_test_api_params()
        example_departure = helpers.generate_departure_details(etd='On time', in_past=False)

        mock_request.return_value = helpers.MockRestResponse(json_content={})
        mock_parser.return_value = [
            example_departure,
            example_departure,
            example_departure
        ]

        departures = data.get_next_departures(test_params, num_departures=3)
        self.assertEqual(len(departures), 3)
        self.assertTupleEqual(departures[0], example_departure)

    @patch('rail_uk.data.make_soap_request')
    @patch('rail_uk.data.parse_departures_soap_response')
    def test_get_next_departures_surplus(self, mock_parser, mock_request):
        test_params = helpers.generate_test_api_params()
        example_departure = helpers.generate_departure_details(etd='On time', in_past=False)

        mock_request.return_value = helpers.MockRestResponse(json_content={})
        mock_parser.return_value = [
            example_departure,
            example_departure,
            example_departure
        ]

        departures = data.get_next_departures(test_params, num_departures=2)
        self.assertEqual(len(departures), 2)
        self.assertTupleEqual(departures[0], example_departure)

    @patch('rail_uk.data.make_soap_request')
    @patch('rail_uk.data.parse_fastest_departure_soap_response')
    def test_get_fastest_departure(self, mock_parser, mock_request):
        test_params = helpers.generate_test_api_params()
        example_departure = helpers.generate_departure_details(etd='On time', in_past=False)

        mock_request.return_value = helpers.MockRestResponse(json_content={})
        mock_parser.return_value = example_departure

        departure = data.get_fastest_departure(test_params)
        self.assertTupleEqual(departure, example_departure)

    @patch('rail_uk.data.get_last_departure_from_timetable')
    @patch('rail_uk.data.datetime')
    @patch('rail_uk.data.get_last_departure_live_time')
    def test_get_last_departure(self, mock_live_etd, mock_time, mock_timetable):
        test_params = helpers.generate_test_api_params()
        test_departure = helpers.generate_departure_details()

        mock_timetable.return_value = test_departure
        mock_time_now = Mock()
        mock_time_now.strftime.return_value = '19:00'
        mock_time.now.return_value = mock_time_now
        mock_live_etd.return_value = None

        departure = data.get_last_departure(test_params)
        self.assertTupleEqual(departure, test_departure)

    @patch('rail_uk.data.get_last_departure_from_timetable')
    @patch('rail_uk.data.datetime')
    def test_get_last_departure_in_past(self, mock_time, mock_timetable):
        test_params = helpers.generate_test_api_params()

        mock_timetable.return_value = helpers.generate_departure_details()
        mock_time_now = Mock()
        mock_time_now.strftime.return_value = '23:00'
        mock_time.now.return_value = mock_time_now

        departure = data.get_last_departure(test_params)
        expected_departure = helpers.generate_departure_details(in_past=True)
        self.assertTupleEqual(departure, expected_departure)

    @patch('rail_uk.data.get_last_departure_from_timetable')
    @patch('rail_uk.data.datetime')
    @patch('rail_uk.data.get_last_departure_live_time')
    def test_get_last_departure_live(self, mock_live_etd, mock_time, mock_timetable):
        test_params = helpers.generate_test_api_params()

        mock_timetable.return_value = helpers.generate_departure_details()
        mock_time_now = Mock()
        mock_time_now.strftime.return_value = '19:00'
        mock_time.now.return_value = mock_time_now
        mock_live_etd.return_value = 'On time'

        departure = data.get_last_departure(test_params)
        expected_departure = helpers.generate_departure_details(etd='On time')
        mock_live_etd.assert_called()
        self.assertTupleEqual(departure, expected_departure)

    # --------------------------- Test Request Helpers ---------------------------

    @patch('rail_uk.data.requests')
    def test_make_soap_request(self, mock_requests):
        mock_params = {
            'access_token': 'MOCK_DARWIN_TOKEN',
            'origin': 'HTX',
            'destination': 'TCX',
            'time_offset': 0,
            'time_window': 120
        }

        test_data = '<TestData>12345</TestData>'
        mock_requests.post.return_value = helpers.MockRestResponse(content=test_data)

        response = data.make_soap_request(mock_params, 'departure_board.xml')
        mock_requests.post.assert_called()
        self.assertEqual(test_data, response)

    @patch('rail_uk.data.get_timetable')
    def test_get_last_departure_from_timetable(self, mock_timetable):
        test_params = helpers.generate_test_api_params()
        mock_timetable.return_value = helpers.generate_test_timetable()
        expected_departure = helpers.generate_departure_details()

        departure = data.get_last_departure_from_timetable(test_params)

        self.assertTupleEqual(departure, expected_departure)
        mock_timetable.assert_called_once()

    @patch('rail_uk.data.get_timetable')
    def test_get_last_departure_from_timetable_early(self, mock_timetable):
        test_params = helpers.generate_test_api_params()
        mock_timetable.side_effect = [None, helpers.generate_test_timetable()]
        expected_departure = helpers.generate_departure_details()

        departure = data.get_last_departure_from_timetable(test_params)

        self.assertTupleEqual(departure, expected_departure)
        self.assertEqual(mock_timetable.call_count, 2)

    @patch('requests.get', side_effect=helpers.generate_mock_rest_response)
    @patch('rail_uk.data.date')
    def test_get_timetable_ok(self, mock_date, mock_api):
        expected_url = 'https://transportapi.com/v3/uk/train/station/HTX/2019-03-01/19:45/timetable.json'
        expected_params = {
            'app_id': 'MOCK_APP_ID',
            'app_key': 'MOCK_API_KEY',
            'calling_at': 'TTX',
            'to_offset': 'PT02:00:00',
            'train_status': 'passenger'
        }
        expected_data = ['Example Departures']
        mock_date.today.return_value = '2019-03-01'

        test_params = helpers.generate_test_api_params()
        result = data.get_timetable(test_params, '19:45')
        self.assertListEqual(result, expected_data)
        mock_api.assert_called_with(expected_url, params=expected_params)

    @patch('requests.get', side_effect=helpers.generate_mock_rest_response)
    @patch('rail_uk.data.date')
    def test_get_timetable_client_err(self, mock_date, _):
        mock_date.today.return_value = '2019-03-01'
        test_params = APIParameters(
            Station('Invalid query', 'XXX'),
            Station('_', '_'),
            offset=0
        )

        with self.assertRaises(ApplicationError) as context:
            data.get_timetable(test_params, '19:45')
        self.assertEqual('Request to TransportAPI failed - Not found', str(context.exception))

    @patch('requests.get', side_effect=helpers.generate_mock_rest_response)
    @patch('rail_uk.data.date')
    def test_get_timetable_api_err(self, mock_date, _):
        mock_date.today.return_value = '2019-03-01'
        test_params = APIParameters(
            Station('Simulated API failure', 'BROKEN'),
            Station('_', '_'),
            offset=0
        )

        with self.assertRaises(TransportAPIError) as context:
            data.get_timetable(test_params, '19:45')
        self.assertEqual('Request to TransportAPI failed - Internal server error', str(context.exception))

    @patch('requests.get', side_effect=helpers.generate_mock_rest_response)
    @patch('rail_uk.data.date')
    def test_get_timetable_unknown_err(self, mock_date, _):
        mock_date.today.return_value = '2019-03-01'
        test_params = APIParameters(
            Station('Simulated new API version', 'UPDATED'),
            Station('_', '_'),
            offset=0
        )

        with self.assertRaises(TransportAPIError) as context:
            data.get_timetable(test_params, '19:45')
        expected_err = 'TransportAPI responded in an unexpected way - \'departures\' not found in response'
        self.assertEqual(expected_err, str(context.exception))

    @patch('rail_uk.data.datetime')
    @patch('rail_uk.data.make_soap_request', return_value=helpers.MockRestResponse(json_content={}))
    @patch('rail_uk.data.parse_departures_soap_response')
    def test_get_last_departure_live_time(self, mock_parser, mock_request, mock_time):
        mock_time_now = Mock()
        mock_time_now.strftime.return_value = '19:45'
        matching_departure = helpers.generate_departure_details(etd='On time')

        mock_time.now.return_value = mock_time_now
        mock_time.strptime.side_effect = datetime.strptime
        mock_parser.return_value = [
            helpers.generate_departure_details(different=True),
            matching_departure
        ]

        test_departure = helpers.generate_departure_details()
        test_params = helpers.generate_test_api_params()
        etd = data.get_last_departure_live_time(test_departure, test_params)

        self.assertEqual(etd, 'On time')
        mock_request.assert_called_once()
        mock_parser.assert_called_once()

    @patch('rail_uk.data.datetime')
    @patch('rail_uk.data.logger')
    def test_get_last_departure_live_not_available(self, mock_logger, mock_time):
        mock_time_now = Mock()
        mock_time_now.strftime.return_value = '16:00'

        mock_time.now.return_value = mock_time_now
        mock_time.strptime.side_effect = datetime.strptime

        mock_departure = helpers.generate_departure_details()
        etd = data.get_last_departure_live_time(mock_departure, None)

        self.assertIsNone(etd)
        mock_logger.debug.assert_called_with('Last train is not close enough to fetch live time')

    @patch('rail_uk.data.datetime')
    @patch('rail_uk.data.make_soap_request', return_value=helpers.MockRestResponse(json_content={}))
    @patch('rail_uk.data.parse_departures_soap_response', return_value=None)
    @patch('rail_uk.data.logger')
    def test_get_last_departure_live_time_no_departures(self, mock_logger, _, __, mock_time):
        mock_time_now = Mock()
        mock_time_now.strftime.return_value = '19:45'

        mock_time.now.return_value = mock_time_now
        mock_time.strptime.side_effect = datetime.strptime

        test_departure = helpers.generate_departure_details()
        test_params = helpers.generate_test_api_params()
        etd = data.get_last_departure_live_time(test_departure, test_params)

        self.assertIsNone(etd)
        mock_logger.warning.assert_called_with('OpenLDBWS returned no live times')

    @patch('rail_uk.data.datetime')
    @patch('rail_uk.data.make_soap_request', return_value=helpers.MockRestResponse(json_content={}))
    @patch('rail_uk.data.parse_departures_soap_response')
    @patch('rail_uk.data.logger')
    def test_get_last_departure_live_time_no_match(self, mock_logger, mock_parser, _, mock_time):
        mock_time_now = Mock()
        mock_time_now.strftime.return_value = '19:45'

        mock_time.now.return_value = mock_time_now
        mock_time.strptime.side_effect = datetime.strptime
        mock_parser.return_value = [
            helpers.generate_departure_details(different=True),
        ]

        test_departure = helpers.generate_departure_details()
        test_params = helpers.generate_test_api_params()
        etd = data.get_last_departure_live_time(test_departure, test_params)

        self.assertIsNone(etd)
        mock_logger.warning.assert_called_with('OpenLDBWS returned no appropriate live time')

    # --------------------------- Test Response Helpers ---------------------------

    def test_parse_departures_soap_response_next(self):
        test_response = helpers.generate_test_soap_response('open_ldbws', 'departure_board.xml')

        departures = data.parse_departures_soap_response(test_response, 'next')
        expected_first_departure = helpers.generate_departure_details(etd='On time')
        self.assertLessEqual(len(departures), 3)
        self.assertTupleEqual(expected_first_departure, departures[0])

    def test_parse_departures_soap_response_last(self):
        test_response = helpers.generate_test_soap_response('open_ldbws', 'departure_board.xml')

        departures = data.parse_departures_soap_response(test_response, 'last')
        expected_first_departure = helpers.generate_departure_details(etd='On time')
        self.assertEqual(len(departures), 10)
        self.assertTupleEqual(expected_first_departure, departures[0])

    @patch('rail_uk.data.handle_soap_fault')
    def test_parse_departures_soap_response_fault(self, mock_fault_handler):
        test_response = helpers.generate_test_soap_response('open_ldbws', 'darwin_fault.xml')
        mock_fault_handler.side_effect = OpenLDBWSError('Request to Darwin failed - Internal server error')
        with self.assertRaises(OpenLDBWSError) as context:
            data.parse_departures_soap_response(test_response, 'last')

        expected_err = 'Request to Darwin failed - Internal server error'
        self.assertEqual(expected_err, str(context.exception))
        mock_fault_handler.assert_called_once()

    @patch('rail_uk.data.logger')
    def test_parse_departures_soap_response_no_departures(self, mock_logger):
        test_response = helpers.generate_test_soap_response('open_ldbws', 'departure_board_empty.xml')

        departures = data.parse_departures_soap_response(test_response, 'last')
        self.assertIsNone(departures)
        mock_logger.warning.assert_called_with('OpenLDBWS returned no departures')

    def test_parse_fastest_departure_soap_response(self):
        test_response = helpers.generate_test_soap_response('open_ldbws', 'fastest_departure.xml')
        departure = data.parse_fastest_departure_soap_response(test_response)
        expected_departure = helpers.generate_departure_details(etd='On time')
        self.assertTupleEqual(departure, expected_departure)

    @patch('rail_uk.data.handle_soap_fault')
    def test_parse_fastest_departure_soap_response_fault(self, mock_fault_handler):
        test_response = helpers.generate_test_soap_response('open_ldbws', 'darwin_fault.xml')
        mock_fault_handler.side_effect = OpenLDBWSError('Request to Darwin failed - Internal server error')
        with self.assertRaises(OpenLDBWSError) as context:
            data.parse_fastest_departure_soap_response(test_response)

        expected_err = 'Request to Darwin failed - Internal server error'
        self.assertEqual(expected_err, str(context.exception))
        mock_fault_handler.assert_called_once()

    @patch('rail_uk.data.logger')
    def test_parse_fastest_departure_soap_response_no_departures(self, mock_logger):
        test_response = helpers.generate_test_soap_response('open_ldbws', 'fastest_departure_empty.xml')

        departures = data.parse_fastest_departure_soap_response(test_response)
        self.assertIsNone(departures)
        mock_logger.warning.assert_called_with('OpenLDBWS returned no departures')

    def test_handle_soap_fault_client(self):
        test_response = helpers.generate_test_soap_response('open_ldbws', 'client_err.xml')
        with self.assertRaises(ApplicationError) as context:
            data.handle_soap_fault(test_response)

        expected_err = 'Request to Darwin failed - Invalid crs code supplied'
        self.assertEqual(expected_err, str(context.exception))

    def test_handle_soap_fault_server(self):
        test_response = helpers.generate_test_soap_response('open_ldbws', 'darwin_fault.xml')
        with self.assertRaises(OpenLDBWSError) as context:
            data.handle_soap_fault(test_response)

        expected_err = 'Request to Darwin failed - Internal server error'
        self.assertEqual(expected_err, str(context.exception))

    def test_handle_soap_fault_unknown(self):
        with self.assertRaises(OpenLDBWSError) as context:
            data.handle_soap_fault('<unknownXML>UH-OH</unknownXML>')

        expected_err = 'Request to Darwin failed - Could not parse response.'
        self.assertEqual(expected_err, str(context.exception))
