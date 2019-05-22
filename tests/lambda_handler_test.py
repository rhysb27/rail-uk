import logging
from unittest import TestCase
from unittest.mock import patch

from rail_uk import lambda_handler
from helpers import helpers


class TestLambdaHandler(TestCase):

    def setUp(self):
        logging.basicConfig(level='DEBUG')
        self.mock_env = helpers.get_test_env()
        self.mock_env.start()

    def tearDown(self):
        self.mock_env.stop()

    def test_lambda_handler_invalid_application_id(self):
        test_event = helpers.generate_test_event('IntentRequest', 'INVALID_ADD_ID')
        with self.assertRaises(ValueError) as context:
            lambda_handler.lambda_handler(test_event, {})
        self.assertEqual('Invalid Application ID', str(context.exception))

    @patch('rail_uk.lambda_handler.on_launch')
    @patch('rail_uk.lambda_handler.logging')
    def test_lambda_handler_launch_request(self, mock_logger, mock_event):
        mock_response = 'Welcome to Rail UK!'
        mock_event.return_value = mock_response
        test_event = helpers.generate_test_event('LaunchRequest')
        response = lambda_handler.lambda_handler(test_event, {})
        mock_logger.info.assert_called_with('Session started: ' + test_event['session']['sessionId'])
        self.assertEqual(response, mock_response)

    @patch('rail_uk.lambda_handler.on_intent')
    def test_lambda_handler_intent_request(self, mock_intent):
        mock_response = 'There are no trains to Train Town at this time.'
        mock_intent.return_value = mock_response
        test_event = helpers.generate_test_event('IntentRequest')

        response = lambda_handler.lambda_handler(test_event, {})
        mock_intent.assert_called_with(test_event['request'], test_event['session'])
        self.assertEqual(response, mock_response)

    @patch('rail_uk.lambda_handler.logging')
    def test_lambda_handler_session_ended_request(self, mock_logger):
        test_event = helpers.generate_test_event('SessionEndedRequest')
        lambda_handler.lambda_handler(test_event, {})
        mock_logger.info.assert_called_with('Session ended: {}'.format(test_event['session']['sessionId']))
