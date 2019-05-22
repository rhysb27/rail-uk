import logging
from fuzzywuzzy import fuzz, process


from rail_uk.dtos import Station, APIParameters, HomeStation
from rail_uk.exceptions import EntityResolutionError, AmbiguousERError
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

    speech = 'I\'m sorry, a problem occurred with one of our data providers. Please try again later ' \
             'and let us know if the problem persists.'

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_db_error_response():
    session_attributes = {}

    speech = 'I\'m sorry, a problem occurred with our data storage provider. Departure queries should still be ' \
             'functional. Please try again later and let us know if the problem persists.'

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_error_response():
    session_attributes = {}

    speech = 'I\'m sorry, something seems to have gone wrong with this skill. We will work on ' \
             'fixing the problem, but if this happens again please let us know.'

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_station_not_found_response(slot_name):
    session_attributes = {}

    speech = 'I\'m sorry, I did not recognise the {} station you requested. We are working on improving our ' \
             'recognition and will release an update soon. In the meantime, please try again.'\
        .format(slot_name)

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=False))


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
    try:
        parameters = get_parameters(intent, session)
    except AmbiguousERError as err:
        slot_name = err[1]
        direction = 'to' if slot_name == 'origin' else 'from'
        message = 'I found {} stations that match the {} you requested. Which specific station would ' \
                  'you like to travel {}?'.format(err[0], slot_name, direction)
        return elicit_slot(slot_name, message)

    if parameters is None:
        return elicit_slot('origin', 'Which station would you like to travel from?')

    departures = data.get_fastest_departure(parameters)

    speech = build_departure_speech(departures, parameters, 'fastest')
    session_attributes = {}

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_next_train(intent, session):
    try:
        parameters = get_parameters(intent, session)
    except AmbiguousERError as err:
        slot_name = err[1]
        direction = 'to' if slot_name == 'origin' else 'from'
        message = 'I found {} stations that match the {} you requested. Which specific station would ' \
                  'you like to travel {}?'.format(err[0], slot_name, direction)
        return elicit_slot(slot_name, message)

    if parameters is None:
        return elicit_slot('origin', 'Which station would you like to travel from?')

    departure = data.get_next_departures(parameters)

    speech = build_departure_speech(departure, parameters, 'next')
    session_attributes = {}

    return build_response(session_attributes, build_speechlet_response(
        speech, reprompt=None, should_end_session=True))


def get_last_train(intent, session):
    try:
        parameters = get_parameters(intent, session)
    except AmbiguousERError as err:
        slot_name = err[1]
        direction = 'to' if slot_name == 'origin' else 'from'
        message = 'I found {} stations that match the {} you requested. Which specific station would ' \
                  'you like to travel {}?'.format(err[0], slot_name, direction)
        return elicit_slot(slot_name, message)

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
    if slot_name not in intent['slots']:
        logger.warning('"{}" slot not found'.format(slot_name))
        return None

    slot = intent['slots'][slot_name]
    logger.warning('SLOT: ' + str(slot))
    if 'value' not in slot:
        logger.warning('"{}" slot not found'.format(slot_name))
        return None

    resolutions = slot['resolutions']['resolutionsPerAuthority'][0]
    if 'values' not in resolutions:
        return resolve_station(slot)

    resolved_slot = resolutions['values'][0]['value']
    station = Station(resolved_slot['name'], resolved_slot['id'])
    logger.debug('Station slot value found ({}): {} '.format(slot_name, station))
    return station


def resolve_station(slot, first_attempt=False):
    # TODO: Catch ambiguityError, track attempts, and set default first_attempt to false
    stations = {}
    with open('res/stations.csv') as csv:
        for row in csv:
            columns = [x.strip() for x in row.split(',')]
            stations[columns[0]] = columns[1]

    matches = process.extract(slot['value'], list(stations.keys()), limit=10, scorer=fuzz.token_sort_ratio)
    best_match = matches[0]

    if first_attempt:
        scores = [match[1] for match in matches]
        max_score = best_match[1]
        ambiguity = scores.count(max_score) + scores.count(max_score - 1) + scores.count(max_score - 2)
        if ambiguity > 1:
            raise AmbiguousERError((ambiguity, slot['name']))

    resolved_station = Station(best_match[0], stations[best_match[0]])
    print(str(resolved_station))
    return resolved_station


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
