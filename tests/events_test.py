from unittest import TestCase
from unittest.mock import patch

from rail_uk import events
from rail_uk.exceptions import OpenLDBWSError, DynamoDBError
from helpers import helpers


class TestEvents(TestCase):

    @patch('rail_uk.events.get_welcome_response')
    @patch('rail_uk.events.logger')
    def test_on_launch(self, mock_logger, mock_welcome):
        _, test_session = helpers.generate_test_data()
        mock_welcome_response = 'Welcome to Rail UK!'
        mock_welcome.return_value = mock_welcome_response

        response = events.on_launch(test_session)
        mock_logger.info.assert_called_with('Launched without intent: ' + test_session['sessionId'])
        mock_welcome.assert_called_once()
        self.assertEqual(response, mock_welcome_response)

    def test_on_intent_ok(self):
        intents = {
            'NextTrain': {
                'handler': 'rail_uk.events.get_next_train',
                'response': 'Next Service Response'
            },
            'FastestTrain': {
                'handler': 'rail_uk.events.get_fastest_train',
                'response': 'Fastest Service Response'
            },
            'LastTrain': {
                'handler': 'rail_uk.events.get_last_train',
                'response': 'Last Service Response'
            },
            'SetHomeStation': {
                'handler': 'rail_uk.events.set_home_station',
                'response': 'Set Home Station Response'
            },
            'AMAZON.HelpIntent': {
                'handler': 'rail_uk.events.get_welcome_response',
                'response': 'Help Response'
            },
            'AMAZON.CancelIntent': {
                'handler': 'rail_uk.events.handle_session_end_request',
                'response': 'Cancel Response'
            },
            'AMAZON.StopIntent': {
                'handler': 'rail_uk.events.handle_session_end_request',
                'response': 'Stop Response'
            }
        }
        for intent in intents:
            test_request, test_session = helpers.generate_test_data(intent=True, intent_name=intent)
            with patch(intents[intent]['handler']) as intent_handler:
                intent_handler.return_value = intents[intent]['response']
                response = events.on_intent(test_request, test_session)
                self.assertEqual(response, intents[intent]['response'])
            intent_handler.assert_called_once()

    @patch('rail_uk.events.get_api_error_response')
    @patch('rail_uk.events.logger')
    @patch('rail_uk.events.get_next_train')
    def test_on_intent_api_error(self, mock_intent, mock_logger, mock_response):
        response_str = 'Sorry, a problem occurred with our data storage provider.'
        mock_response.return_value = response_str
        mock_intent.side_effect = OpenLDBWSError('OpenLDBWS failed for unknown reason')

        test_request, test_session = helpers.generate_test_data(intent=True, intent_name="NextTrain")
        response = events.on_intent(test_request, test_session)

        mock_logger.exception.assert_called_with('-[API ERROR]- Upstream API failed:')
        self.assertEqual(response_str, response)

    @patch('rail_uk.events.get_db_error_response')
    @patch('rail_uk.events.logger')
    @patch('rail_uk.events.set_home_station')
    def test_on_intent_db_error(self, mock_intent, mock_logger, mock_response):
        response_str = 'Sorry, a problem occurred with one of our data providers.'
        mock_response.return_value = response_str
        mock_intent.side_effect = DynamoDBError('DynamoDB failed to update home station')

        test_request, test_session = helpers.generate_test_data(intent=True, intent_name="SetHomeStation")
        response = events.on_intent(test_request, test_session)

        mock_logger.exception.assert_called_with('-[DYNAMODB ERROR]- DynamoDB failed to set/update user details:')
        self.assertEqual(response_str, response)

    @patch('rail_uk.events.get_error_response')
    @patch('rail_uk.events.logger')
    def test_on_intent_error(self, mock_logger, mock_response):
        response_str = 'Sorry, something seems to have gone wrong with this skill.'
        mock_response.return_value = response_str

        test_request, test_session = helpers.generate_test_data(intent=True, intent_name="NotYetImplementedIntent")
        response = events.on_intent(test_request, test_session)

        mock_logger.exception.assert_called_with('-[RAIL UK ERROR]- Rail UK encountered an exception:')
        self.assertEqual(response_str, response)


# def helpers.generate_test_data(intent=False, intent_name=None):
#     if intent:
#         test_request = {
#             'type': 'IntentRequest',
#             'requestId': 'amzn1.echo-api.request.TEST',
#             'intent': {
#                 'name': intent_name,
#             },
#         }
#     else:
#         test_request = {
#             'requestId': 'amzn1.echo-api.request.TEST'
#         }
#     test_session = {
#         'sessionId': 'amzn1.echo-api.session.TEST',
#         'application': {
#             'applicationId': 'amzn1.ask.skill.TEST'
#         },
#         'user': {
#             'userId': 'amzn1.ask.account.TEST'
#         }
#     }
#     return test_request, test_session
