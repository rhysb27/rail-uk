import logging

from rail_uk.dtos import Station, APIParameters, HomeStation
from rail_uk import data
from rail_uk import dynamodb

logger = logging.getLogger(__name__)


# ----------------------------- Simple Responses -----------------------------

def get_welcome_response():
    session_attributes = {}

    speech = 'Welcome to Rail UK. You can start by asking me for the next, fastest or last ' \
             'train to any UK rail station, or asking me to set your home station.'
    reprompt = 'What can I do for you today?'

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt, should_end_session=False))


def handle_session_end_request():
    speech = 'Travel safe.'
    return build_response({}, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_api_error_response():
    session_attributes = {}

    speech = 'Sorry, a problem occurred with one of our data providers. Please try again later ' \
             'and let us know if the problem persists.'

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_db_error_response():
    session_attributes = {}

    speech = 'Sorry, a problem occurred with our data storage provider. Departure queries should still be ' \
             'functional. Please try again later and let us know if the problem persists.'

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_error_response():
    session_attributes = {}

    speech = 'Sorry, something seems to have gone wrong with this skill. We are probably already working on ' \
             'fixing the problem, but if this happens again please let us know.'

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


# ----------------------------- Complex Responses -----------------------------

def set_home_station(intent, session):
    user_id = session['user']['userId']
    station = get_station_from_slot(intent, 'home')
    distance = get_slot_value(intent, 'distance')

    details = HomeStation(station, distance)

    result = dynamodb.set_home_station(user_id, details)
    speech = 'Your home station has been {}.'.format(result)

    session_attributes = {}
    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_fastest_train(intent, session):
    parameters = get_parameters(intent, session)
    if parameters is None:
        return elicit_slot('origin', 'Which station would you like to travel from?')

    departures = data.get_fastest_departure(parameters)

    speech = build_departure_speech(departures, parameters, 'fastest')
    session_attributes = {}

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_next_train(intent, session):
    parameters = get_parameters(intent, session)
    if parameters is None:
        return elicit_slot('origin', 'Which station would you like to travel from?')

    departure = data.get_next_departures(parameters)

    speech = build_departure_speech(departure, parameters, 'next')
    session_attributes = {}

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_last_train(intent, session):
    parameters = get_parameters(intent, session)
    if parameters is None:
        return elicit_slot('origin', 'Which station would you like to travel from?')

    departure = data.get_last_departure(parameters)

    speech = build_last_departure_speech(departure, parameters)
    session_attributes = {}

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


# ----------------------------- Misc Helpers -----------------------------

def get_parameters(intent, session):
    origin_from_slot = get_station_from_slot(intent, 'origin')
    if origin_from_slot is None:
        user_id = session['user']['userId']
        home = dynamodb.get_home_station(user_id)
        if home is None:
            return None

        origin = home.station
        offset = home.distance
    else:
        origin = origin_from_slot
        offset = 0

    destination = get_station_from_slot(intent, 'destination')

    return APIParameters(origin, destination, offset)


def get_station_from_slot(intent, slot_name):
    try:
        slot = intent['slots'][slot_name]['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']
        station = Station(slot['name'], slot['id'])
        logger.debug('Station slot value found ({}): {} '.format(slot_name, station))
        return station
    except KeyError:
        logger.warning('Slot value not found: ' + slot_name)
        return None


def get_slot_value(intent, slot_name):
    try:
        value = intent['slots'][slot_name]['value']
        logger.debug('Slot value found ({}): {} '.format(slot_name, value))
        return value
    except KeyError:
        logger.warning('Slot value not found: ' + slot_name)
        return None


# ----------------------------- Response Helpers -----------------------------

def elicit_slot(slot_name, prompt):
    directives = [
        {
            'type': 'Dialog.ElicitSlot',
            'slotToElicit': slot_name
        }
    ]
    session_attributes = {}

    response = build_response(session_attributes, build_speechlet_response(
        speech=prompt,
        reprompt=prompt,
        should_end_session=False,
        directives=directives))

    return response


def build_departure_speech(departure, api_params, intent_type):
    if departure is None:
        departure_detail_template = 'I cannot find a train to {} from {} at this time.'
        return departure_detail_template.format(api_params.destination.name,
                                                api_params.origin.name)

    departure_detail_template = 'The {} train to {} from {} is the {} {} service to {}'
    departure_details = departure_detail_template.format(intent_type,
                                                         api_params.destination.name,
                                                         api_params.origin.name,
                                                         departure.std,
                                                         departure.operator,
                                                         departure.final_dest)
    if departure.live:
        if departure.etd == 'On time':
            service_status = ', which is running on time.'
        else:
            service_status = ', which will likely depart at around {}.'.format(departure.etd)
    else:
        service_status = '.'

    return departure_details + service_status


def build_last_departure_speech(departure, api_params):
    if departure is None:
        departure_detail_template = 'I cannot find a train to {} from {} today.'
        return departure_detail_template.format(api_params.destination.name,
                                                api_params.origin.name)

    if departure.in_past:
        tense = 'was'
    else:
        tense = 'is'

    departure_detail_template = 'The last train to {} from {} {} the {} {} service to {}'
    departure_details = departure_detail_template.format(api_params.destination.name,
                                                         api_params.origin.name,
                                                         tense,
                                                         departure.std,
                                                         departure.operator,
                                                         departure.final_dest)

    if departure.live:
        if departure.etd == 'On time':
            service_status = ', which is running on time.'
        else:
            service_status = ', which will likely depart at around {}.'.format(departure.etd)
    else:
        service_status = '.'

    return departure_details + service_status


def build_speechlet_response(speech, reprompt, should_end_session, directives=None):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': speech
        },
        'card': {
            'type': 'Simple',
            'title': 'Rail UK',
            'content': speech
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt
            }
        },
        'directives': [] if directives is None else directives,
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }
