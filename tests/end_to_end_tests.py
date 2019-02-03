import logging
from os import environ
from jinja2 import Environment, FileSystemLoader
from unittest import TestCase
from unittest.mock import patch

from lambda_entry import lambda_handler
from helpers import helpers


class TestEndToEnd(TestCase):

    def setUp(self):
        logging.basicConfig(level='DEBUG')
        self.mock_env = helpers.get_test_env()
        self.mock_env.start()
        self.default_slots = {
            'destination': {
                'name': 'Train Town',
                'id': 'TTX'
            },
            'origin': {
                'name': 'Home Town',
                'id': 'HTX'
            }
        }

    def tearDown(self):
        self.mock_env.stop()

    @patch('rail_uk.data.make_soap_request')
    def test_fastest_train(self, mock_request):
        mock_request.return_value = _mock_soap_response(self.default_slots, 'open_ldbws', 'fastest_departure.xml')
        response = lambda_handler(_make_mock_event('FastestTrain', self.default_slots), None)
        speech = response['response']['outputSpeech']['text']
        expected_speech = 'The fastest train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                          'service to Train City, which is running on time.'
        self.assertEqual(speech, expected_speech)

    @patch('rail_uk.data.make_soap_request')
    def test_next_train(self, mock_request):
        mock_request.return_value = _mock_soap_response(self.default_slots, 'open_ldbws', 'departure_board.xml')
        response = lambda_handler(_make_mock_event('NextTrain', self.default_slots), None)
        speech = response['response']['outputSpeech']['text']
        expected_speech = 'The next train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                          'service to Train City, which is running on time.'
        self.assertEqual(speech, expected_speech)

    @patch('requests.get')
    @patch('rail_uk.data.get_last_departure_live_time', return_value=None)
    def test_last_train(self, _, mock_timetable_request):
        request_vars = {
            'origin_name': self.default_slots['origin']['name'],
            'origin_crs': self.default_slots['origin']['id']
        }
        mock_timetable_request.return_value = helpers.generate_test_rest_response(request_vars)
        response = lambda_handler(_make_mock_event('LastTrain', self.default_slots), None)
        speech = response['response']['outputSpeech']['text']
        expected_speech = 'The last train to Train Town from Home Town is the 22:00 Train Operator Limited ' \
                          'service to Train City.'
        self.assertEqual(speech, expected_speech)


# ---------------------------------  Helpers ---------------------------------

def _make_mock_event(intent_name, intent_slots_):
    event = {
        'version': '1.0',
        'session': {
            'new': True,
            'sessionId': 'amzn1.echo-api.session.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
            'application': {
                'applicationId': environ['SKILL_ID']
            },
            'user': {
                'userId': 'amzn1.ask.account.xxxxxxxxxxxx'
            }
        },
        'context': {
            'System': {
                'application': {
                    'applicationId': environ['SKILL_ID']
                },
                'user': {
                    'userId': 'amzn1.ask.account.xxxxxxxxxxxx'
                },
                'apiAccessToken': 'xxxxxxxx'
            }
        },
        'request': {
            'type': 'IntentRequest',
            'requestId': 'amzn1.echo-api.request.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
            'intent': {
                'name': intent_name,
                'slots': _expand_slots(intent_slots_)
            }
        },
    }
    return event


def _expand_slots(intent_slots_):
    slot_dict = {}
    for slot in intent_slots_:
        slot_dict[slot] = _expand_slot(slot, intent_slots_[slot])

    return slot_dict


def _expand_slot(slot_name, slot_values):
    return {
        'name': slot_name,
        'resolutions': {
            'resolutionsPerAuthority': [{
                'values': [{
                    'value': slot_values
                }]
            }]
        }
    }


def _mock_soap_response(intent_slots_, data_source, template_file):
    params = {
        'origin_name': intent_slots_['origin']['name'],
        'origin_crs': intent_slots_['origin']['id'],
        'destination_name': intent_slots_['destination']['name'],
        'destination_crs': intent_slots_['destination']['id']
    }
    template_loader = FileSystemLoader(searchpath='tests/mock_responses/{}/'.format(data_source))
    template_env = Environment(loader=template_loader)
    template = template_env.get_template(template_file)
    return template.render(req_vars=params)
