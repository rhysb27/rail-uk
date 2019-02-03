import json
from os import environ
from unittest.mock import patch
from jinja2 import FileSystemLoader, Environment
from rail_uk.dtos import APIParameters, Station, DepartureInfo


# ------------- Environment Manager -------------

def get_test_env():
    return patch.dict(environ, {
        'SKILL_ID': 'amzn1.ask.skill.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
        'OPEN_LDBWS_ACCESS_TOKEN': 'MOCK_DARWIN_TOKEN',
        'TRANSPORT_API_APP_ID': 'MOCK_APP_ID',
        'TRANSPORT_API_KEY': 'MOCK_API_KEY'
    })


# ------------- DTO generators -------------

def generate_test_api_params():
    return APIParameters(
        origin=Station('Home Town', 'HTX'),
        destination=Station('Train Town', 'TTX'),
        offset=0
    )


def generate_departure_details(etd='22:00', in_past=False, different=False):
    if different:
        return DepartureInfo(
            std='21:51',
            etd=etd,
            operator='Midland Rail',
            final_dest='Train Town',
            in_past=in_past,
            live=(etd != '22:00')
        )
    else:
        return DepartureInfo(
            std='22:00',
            etd=etd,
            operator='Train Operator Limited',
            final_dest='Train City',
            in_past=in_past,
            live=(etd != '22:00')
        )


# ------------- Response/partial response generators -------------

class MockRestResponse:

    def __init__(self, json_content=None, content=None, status_code=200):
        self.json_content = json_content
        self.content = content
        self.status_code = status_code
        reason_dict = {
            200: 'OK',
            404: 'Not found',
            500: 'Internal server error'
        }
        self.reason = reason_dict[status_code]
        self.ok = status_code == 200

    def json(self):
        return self.json_content


def generate_mock_rest_response(*args, **_):
    if args[0] == 'https://transportapi.com/v3/uk/train/station/HTX/2019-03-01/19:45/timetable.json':
        return MockRestResponse(json_content={
            'departures': {
                'all': ['Example Departures']
            }
        }, status_code=200)
    elif args[0] == 'https://transportapi.com/v3/uk/train/station/UPDATED/2019-03-01/19:45/timetable.json':
        return MockRestResponse(json_content={
            'all_departures': ['Example Departures']
        }, status_code=200)
    elif args[0] == 'https://transportapi.com/v3/uk/train/station/BROKEN/2019-03-01/19:45/timetable.json':
        return MockRestResponse(None, status_code=500)

    return MockRestResponse(None, status_code=404)


def generate_test_rest_response(params=None):
    with open('tests/mock_responses/transport_api/timetable.json', 'r') as file:
        data = file.read() \
            .replace('{{ name }}', 'Home Town' if params is None else params['origin_name']) \
            .replace('{{ crs }}', 'HTX' if params is None else params['origin_crs'])

    return MockRestResponse(json_content=json.loads(data))


def generate_test_timetable():
    response = generate_test_rest_response()
    data = response.json()
    return data['departures']['all']


def generate_test_soap_response(data_source, template_file):
    params = {
        'origin_name': 'Home Town',
        'origin_crs': 'HTX',
        'destination_name': 'Train Town',
        'destination_crs': 'TTX'
    }
    template_loader = FileSystemLoader(searchpath='tests/mock_responses/{}/'.format(data_source))
    template_env = Environment(loader=template_loader)
    template = template_env.get_template(template_file)
    return template.render(req_vars=params)


# ------------- Incoming request / partial request generators -------------

def generate_test_intent():
    return {
        "name": "SetHomeStation",
        "slots": {
            "distance": {
                "name": "distance",
                "value": 10,
            },
            "home": {
                "name": "home",
                "value": "5 ways",
                "resolutions": {
                    "resolutionsPerAuthority": [{
                        "values": [{
                            "value": {
                                "name": "Home Town",
                                "id": "HTX"
                            }
                        }]
                    }]
                }
            }
        }
    }


def generate_test_data(intent=False, intent_name=None):
    if intent:
        test_request = {
            'type': 'IntentRequest',
            'requestId': 'amzn1.echo-api.request.TEST',
            'intent': {
                'name': intent_name,
            },
        }
    else:
        test_request = {
            'requestId': 'amzn1.echo-api.request.TEST'
        }
    test_session = {
        'sessionId': 'amzn1.echo-api.session.TEST',
        'application': {
            'applicationId': 'amzn1.ask.skill.TEST'
        },
        'user': {
            'userId': 'amzn1.ask.account.TEST'
        }
    }
    return test_request, test_session


def generate_test_event(request_type, app_id=None):
    return {
        'session': {
            'new': (request_type == 'LaunchRequest'),
            'sessionId': 'amzn1.echo-api.session.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
            'application': {
                'applicationId': environ['SKILL_ID'] if app_id is None else app_id
            }
        },
        'context': {},
        'request': {
            'type': request_type
        },
    }
