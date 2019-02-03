import logging
from unittest import TestCase
from unittest.mock import patch

from rail_uk import intents
from rail_uk.dtos import APIParameters, Station, HomeStation
from helpers import helpers


class TestIntents(TestCase):

    def setUp(self):
        logging.basicConfig(level='DEBUG')

    # --------------------------- Test Simple Responses ---------------------------

    def test_get_welcome_response(self):
        expected_speech = 'Welcome to Rail UK. You can start by asking me for ' \
                          'the next, fastest or last train to any UK rail station, ' \
                          'or asking me to set your home station.'
        expected_reprompt = 'What can I do for you today?'

        response = intents.get_welcome_response()
        _test_response(response, expected_speech, expected_reprompt, should_end_session=False)

    def test_handle_session_end_request(self):
        expected_speech = 'Travel safe.'

        response = intents.handle_session_end_request()
        _test_response(response, expected_speech, expected_reprompt=None, should_end_session=True)

    def test_get_api_error_response(self):
        expected_speech = 'Sorry, a problem occurred with one of our data providers. Please try again later ' \
             'and let us know if the problem persists.'

        response = intents.get_api_error_response()
        _test_response(response, expected_speech, expected_reprompt=None, should_end_session=True)

    def test_get_db_error_response(self):
        expected_speech = 'Sorry, a problem occurred with our data storage provider. Departure queries should ' \
                'still be functional. Please try again later and let us know if the problem persists.'

        response = intents.get_db_error_response()
        _test_response(response, expected_speech, expected_reprompt=None, should_end_session=True)

    def test_get_error_response(self):
        expected_speech = 'Sorry, something seems to have gone wrong with this skill. We are probably already ' \
                'working on fixing the problem, but if this happens again please let us know.'

        response = intents.get_error_response()
        _test_response(response, expected_speech, expected_reprompt=None, should_end_session=True)

    # -------------------------- Test Complex Responses --------------------------

    @patch('rail_uk.intents.get_station_from_slot')
    @patch('rail_uk.intents.get_slot_value')
    @patch('rail_uk.intents.dynamodb')
    def test_set_home_station(self, mock_db, mock_slot, mock_station):
        mock_session = {
            'user': {'userId': 'TEST_ID'}
        }
        mock_station.return_value = Station('Train Town', 'TTX')
        mock_slot.return_value = 10
        mock_db.set_home_station.return_value = 'set'
        expected_speech = 'Your home station has been set.'

        response = intents.set_home_station({}, mock_session)
        _test_response(response, expected_speech, expected_reprompt=None, should_end_session=True)

    @patch('rail_uk.intents.get_parameters')
    @patch('rail_uk.intents.data')
    def test_get_fastest_train(self, mock_data, mock_params):
        mock_params.return_value = helpers.generate_test_api_params()
        mock_data.get_fastest_departure.return_value = helpers.generate_departure_details(etd='On time', in_past=False)
        expected_speech = 'The fastest train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                          'service to Train City, which is running on time.'
        response = intents.get_fastest_train({}, {})
        _test_response(response, expected_speech, expected_reprompt=None, should_end_session=True)

    @patch('rail_uk.intents.get_parameters')
    def test_get_fastest_train_no_origin(self, mock_params):
        mock_params.return_value = None
        expected_speech = 'Which station would you like to travel from?'

        response = intents.get_fastest_train({}, {})
        _test_response(response, expected_speech, expected_reprompt=expected_speech, should_end_session=False)

    @patch('rail_uk.intents.get_parameters')
    @patch('rail_uk.intents.data')
    def test_get_next_train(self, mock_data, mock_params):
        mock_params.return_value = helpers.generate_test_api_params()
        mock_data.get_next_departures.return_value = helpers.generate_departure_details(etd='On time', in_past=False)
        expected_speech = 'The next train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                          'service to Train City, which is running on time.'
        response = intents.get_next_train({}, {})
        _test_response(response, expected_speech, expected_reprompt=None, should_end_session=True)

    @patch('rail_uk.intents.get_parameters')
    def test_get_next_train_no_origin(self, mock_params):
        mock_params.return_value = None
        expected_speech = 'Which station would you like to travel from?'

        response = intents.get_next_train({}, {})
        _test_response(response, expected_speech, expected_reprompt=expected_speech, should_end_session=False)

    @patch('rail_uk.intents.get_parameters')
    @patch('rail_uk.intents.data')
    def test_get_last_train(self, mock_data, mock_params):
        mock_params.return_value = helpers.generate_test_api_params()
        mock_data.get_last_departure.return_value = helpers.generate_departure_details(etd='On time', in_past=False)
        expected_speech = 'The last train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                          'service to Train City, which is running on time.'
        response = intents.get_last_train({}, {})
        _test_response(response, expected_speech, expected_reprompt=None, should_end_session=True)

    @patch('rail_uk.intents.get_parameters')
    def test_get_last_train_no_origin(self, mock_params):
        mock_params.return_value = None
        expected_speech = 'Which station would you like to travel from?'

        response = intents.get_last_train({}, {})
        _test_response(response, expected_speech, expected_reprompt=expected_speech, should_end_session=False)

    # --------------------------- Test Misc Helpers ------------------------------

    @patch('rail_uk.intents.get_station_from_slot')
    def test_get_parameters(self, mock_slot):
        mock_origin = Station('Train Town', 'TTX')
        mock_destination = Station('Train City', 'TCX')
        mock_slot.side_effect = [mock_origin, mock_destination]
        parameters = intents.get_parameters({}, {})
        expected_parameters = APIParameters(mock_origin, mock_destination, 0)

        self.assertEqual(mock_slot.call_count, 2)
        self.assertTupleEqual(parameters, expected_parameters)

    @patch('rail_uk.intents.get_station_from_slot')
    @patch('rail_uk.intents.dynamodb')
    def test_get_parameters_origin_from_dynamodb(self, mock_db, mock_slot):
        mock_origin = Station('Home Town', 'HTX')
        mock_destination = Station('Train City', 'TCX')
        mock_session = {
            'user': {'userId': 'TEST_ID'}
        }
        mock_slot.side_effect = [None, mock_destination]
        mock_db.get_home_station.return_value = HomeStation(mock_origin, 10)

        parameters = intents.get_parameters({}, mock_session)
        expected_parameters = APIParameters(mock_origin, mock_destination, 10)

        mock_db.get_home_station.assert_called_with('TEST_ID')
        self.assertEqual(mock_slot.call_count, 2)
        self.assertTupleEqual(parameters, expected_parameters)

    @patch('rail_uk.intents.get_station_from_slot')
    @patch('rail_uk.intents.dynamodb')
    def test_get_parameters_no_origin_or_home(self, mock_db, mock_slot):
        mock_session = {
            'user': {'userId': 'TEST_ID'}
        }
        mock_slot.return_value = None
        mock_db.get_home_station.return_value = None
        parameters = intents.get_parameters({}, mock_session)

        mock_db.get_home_station.assert_called_with('TEST_ID')
        mock_slot.assert_called_once()
        self.assertIsNone(parameters)

    def test_get_station_from_slot_ok(self):
        test_intent = helpers.generate_test_intent()
        station = intents.get_station_from_slot(test_intent, 'home')
        expected_station = Station(name='Home Town', crs='HTX')
        self.assertTupleEqual(station, expected_station)

    def test_get_station_from_slot_err(self):
        test_intent = helpers.generate_test_intent()
        station = intents.get_station_from_slot(test_intent, 'bad_slot_name')
        self.assertIsNone(station)

    def test_get_slot_value_ok(self):
        test_intent = helpers.generate_test_intent()
        slot_value = intents.get_slot_value(test_intent, 'distance')
        self.assertEqual(slot_value, 10)

    def test_get_slot_value_err(self):
        test_intent = helpers.generate_test_intent()
        slot_value = intents.get_slot_value(test_intent, 'bad_slot_name')
        self.assertIsNone(slot_value)

    # -------------------------- Test Response Helpers ---------------------------

    def test_elicit_slot(self):
        test_prompt = 'Which station would you like to travel from?'
        expected_directives = [{
            'type': 'Dialog.ElicitSlot',
            'slotToElicit': 'origin'
        }]

        response = intents.elicit_slot('origin', test_prompt)
        response_directives = response['response']['directives']
        _test_response(response, test_prompt, expected_reprompt=test_prompt, should_end_session=False)
        self.assertListEqual(response_directives, expected_directives)

    def test_build_departure_speech_no_trains(self):
        response = intents.build_departure_speech(None, helpers.generate_test_api_params(), 'next')
        expected_response = 'I cannot find a train to Train Town from Home Town at this time.'
        self.assertEqual(response, expected_response)

    def test_build_departure_speech(self):
        test_departure = helpers.generate_departure_details()
        response = intents.build_departure_speech(test_departure, helpers.generate_test_api_params(), 'next')
        expected_response = 'The next train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                            'service to Train City.'
        self.assertEqual(response, expected_response)

    def test_build_departure_speech_live_on_time(self):
        test_departure = helpers.generate_departure_details(etd='On time')
        response = intents.build_departure_speech(test_departure, helpers.generate_test_api_params(), 'next')
        expected_response = 'The next train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                            'service to Train City, which is running on time.'
        self.assertEqual(response, expected_response)

    def test_build_departure_speech_live_late(self):
        test_departure = helpers.generate_departure_details(etd='20:10')
        response = intents.build_departure_speech(test_departure, helpers.generate_test_api_params(), 'next')
        expected_response = 'The next train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                            'service to Train City, which will likely depart at around 20:10.'
        self.assertEqual(response, expected_response)

    def test_build_last_departure_speech_no_trains(self):
        response = intents.build_last_departure_speech(None, helpers.generate_test_api_params())
        expected_response = 'I cannot find a train to Train Town from Home Town today.'
        self.assertEqual(response, expected_response)

    def test_build_last_departure_speech(self):
        test_departure = helpers.generate_departure_details()
        response = intents.build_last_departure_speech(test_departure, helpers.generate_test_api_params())
        expected_response = 'The last train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                            'service to Train City.'
        self.assertEqual(response, expected_response)

    def test_build_last_departure_speech_in_past(self):
        test_departure = helpers.generate_departure_details(in_past=True)
        response = intents.build_last_departure_speech(test_departure, helpers.generate_test_api_params())
        expected_response = 'The last train to Train Town from Home Town was the 22:00 Train Operator Limited ' \
                            'service to Train City.'
        self.assertEqual(response, expected_response)

    def test_build_last_departure_speech_live_on_time(self):
        test_departure = helpers.generate_departure_details(etd='On time')
        response = intents.build_last_departure_speech(test_departure, helpers.generate_test_api_params())
        expected_response = 'The last train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                            'service to Train City, which is running on time.'
        self.assertEqual(response, expected_response)

    def test_build_last_departure_speech_live_late(self):
        test_departure = helpers.generate_departure_details(etd='20:10')
        response = intents.build_last_departure_speech(test_departure, helpers.generate_test_api_params())
        expected_response = 'The last train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                            'service to Train City, which will likely depart at around 20:10.'
        self.assertEqual(response, expected_response)

    def test_build_speechlet_response(self):
        test_speech = 'This is a test.'
        test_reprompt = 'This is STILL a test.'

        expected_response = {
            'outputSpeech': {
                'type': 'PlainText',
                'text': test_speech
            },
            'card': {
                'type': 'Simple',
                'title': 'Rail UK',
                'content': test_speech
            },
            'reprompt': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': test_reprompt
                }
            },
            'directives': [],
            'shouldEndSession': False
        }
        response = intents.build_speechlet_response(test_speech, test_reprompt, False)
        self.assertDictEqual(response, expected_response)

    def test_build_speechlet_response_with_directives(self):
        test_speech = 'This is a test with directives'
        test_reprompt = None

        directives = [
            {
                'type': 'Test',
                'slotToElicit': 'origin'
            }
        ]
        response = intents.build_speechlet_response(test_speech, test_reprompt, False, directives)
        response_directives = response['directives']
        self.assertListEqual(response_directives, directives)

    def test_build_response(self):
        test_session_attributes = {
            'example_attribute': 12345,
            'follow_up_attribute': 'Test'
        }
        test_speechlet = 'This is a test'

        expected_response = {
            'version': '1.0',
            'sessionAttributes': test_session_attributes,
            'response': test_speechlet
        }

        response = intents.build_response(test_session_attributes, test_speechlet)
        self.assertDictEqual(response, expected_response)


def _test_response(response, expected_speech, expected_reprompt, should_end_session):
    speech = response['response']['outputSpeech']['text']
    reprompt = response['response']['reprompt']['outputSpeech']['text']
    ends_session = response['response']['shouldEndSession']

    assert(speech == expected_speech)
    if expected_reprompt is None:
        assert(reprompt is None)
    else:
        assert(reprompt == expected_reprompt)
    assert(ends_session == should_end_session)
