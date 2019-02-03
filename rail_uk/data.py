import logging
from os import environ

import requests
import jinja2
import xmltodict
from datetime import date, datetime, timedelta
from xml.dom import minidom

from rail_uk.exceptions import ApplicationError, OpenLDBWSError, TransportAPIError
from rail_uk.dtos import DepartureInfo

logger = logging.getLogger(__name__)


def get_next_departures(params, num_departures=1):
    request_vars = {
        'access_token': environ['OPEN_LDBWS_ACCESS_TOKEN'],
        'origin': params.origin.crs,
        'destination': params.destination.crs,
        'time_offset': params.offset,
        'time_window': 120
    }
    response = make_soap_request(request_vars, 'departure_board.xml')

    departures = parse_departures_soap_response(response, 'next')

    if departures is None:
        return None
    if num_departures == 1:
        return departures[0]
    if len(departures) == num_departures:
        return departures

    return departures[0:num_departures]


def get_fastest_departure(params):
    request_vars = {
        'access_token': environ['OPEN_LDBWS_ACCESS_TOKEN'],
        'origin': params.origin.crs,
        'destination': params.destination.crs,
        'time_offset': params.offset,
        'time_window': 120
    }
    response = make_soap_request(request_vars, 'fastest_departure.xml')

    return parse_fastest_departure_soap_response(response)


def get_last_departure(params):
    last_departure = get_last_departure_from_timetable(params)
    now = datetime.now()
    now_string = now.strftime('%H:%M')
    if last_departure.std < now_string:
        logger.debug('Last departure is in the past')
        return DepartureInfo(last_departure.std,
                             last_departure.etd,
                             last_departure.operator,
                             last_departure.final_dest,
                             in_past=True,
                             live=False)
    else:
        live_etd = get_last_departure_live_time(last_departure, params)
        if live_etd is not None:
            return DepartureInfo(last_departure.std,
                                 live_etd,
                                 last_departure.operator,
                                 last_departure.final_dest,
                                 in_past=False,
                                 live=True)

    return last_departure


# ----------------------------- Request Helpers -----------------------------

def make_soap_request(params, template_file):
    template_loader = jinja2.FileSystemLoader(searchpath="res/templates/")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template(template_file)

    body = template.render(req_vars=params)
    url = "https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb9.asmx"
    headers = {'content-type': 'text/xml'}

    logger.debug('OpenLDBWS request: {} \nBody: {}'.format(url, body))
    response = requests.post(url, data=body, headers=headers)

    debug_str = minidom.parseString(response.content).toprettyxml()
    logger.debug('OpenLDBWS response: \n' + debug_str)
    return response.content


def get_last_departure_from_timetable(params):
    departures = None
    time = '21:59'
    cutoff = '10:00'

    while departures is None or time < cutoff:
        departures = get_timetable(params, time)
        if departures is None:
            logger.info('Abnormally early last train')
            time = (datetime.strptime(time, '%H:%M') - timedelta(hours=2)).strftime('%H:%M')

    latest_departure = {'aimed_departure_time': '00:00'}
    for departure in departures:
        this_time = departure['aimed_departure_time']
        if this_time > latest_departure['aimed_departure_time']:
            latest_departure = departure

    return DepartureInfo(latest_departure['aimed_departure_time'],
                         latest_departure['aimed_departure_time'],
                         latest_departure['operator_name'],
                         latest_departure['destination_name'],
                         in_past=False,
                         live=False)


def get_timetable(params, time):
    url = 'https://transportapi.com/v3/uk/train/station/{origin}/{date}/{time}/timetable.json'.format(
        origin=params.origin.crs,
        date=str(date.today()),
        time=str(time)
    )

    param_dict = {
        'app_id': environ['TRANSPORT_API_APP_ID'],
        'app_key': environ['TRANSPORT_API_KEY'],
        'calling_at': params.destination.crs,
        'to_offset': 'PT02:00:00',
        'train_status': 'passenger'
    }
    response = requests.get(url, params=param_dict)

    if response.ok:
        logger.debug('TransportAPI response: \n' + str(response.json()))
        data = response.json()
        try:
            return data['departures']['all']
        except KeyError as err:
            msg = 'TransportAPI responded in an unexpected way - {} not found in response'.format(err)
            logger.error(msg)
            raise TransportAPIError(msg)
    elif response.status_code < 499:
        logger.error('TransportAPI rejected request')
        raise ApplicationError('Request to TransportAPI failed - ' + response.reason)
    else:
        logger.error('TransportAPI returned HTTP status 5xx')
        raise TransportAPIError('Request to TransportAPI failed - ' + response.reason)


def get_last_departure_live_time(departure, params):
    time_format = '%H:%M'
    now = datetime.now()
    now_string = now.strftime(time_format)
    departure_time = departure.std
    t_delta = datetime.strptime(departure_time, time_format) - datetime.strptime(now_string, time_format)
    delta_hours = t_delta.seconds//3600
    # Live times only available within 2 hours
    if delta_hours > 2:
        logger.debug('Last train is not close enough to fetch live time')
        return None

    logger.debug('Fetching live time for last train')
    request_vars = {
        'type': 'Next',
        'access_token': environ['OPEN_LDBWS_ACCESS_TOKEN'],
        'origin': params.origin.crs,
        'destination': params.destination.crs,
        'time_offset': (t_delta.seconds//60) - 10,
        'time_window': 20
    }
    response = make_soap_request(request_vars, 'departures.xml')

    live_departures = parse_departures_soap_response(response, 'last')
    if live_departures is None:
        logger.warning('OpenLDBWS returned no live times')
        return None

    for live_departure in live_departures:
        match = live_departure.std == departure.std and \
                live_departure.operator == departure.operator and \
                live_departure.final_dest == departure.final_dest
        if match:
            return live_departure.etd
    logger.warning('OpenLDBWS returned no appropriate live time')
    return None


# -----------------------------  Response Helpers -----------------------------

def parse_departures_soap_response(response, request_type):
    departure_board = None
    try:
        raw_dict = xmltodict.parse(response)
        departure_board = raw_dict['soap:Envelope']['soap:Body']['GetDepartureBoardResponse']['GetStationBoardResult']
    except (KeyError, Exception):
        handle_soap_fault(response)

    # Make sure there is at least one service available
    if 'lt5:trainServices' not in departure_board:
        logger.warning('OpenLDBWS returned no departures')
        return None
    all_departures = departure_board['lt5:trainServices']['lt5:service']

    if request_type == 'next':
        max_list_size = 3
    else:
        max_list_size = 10

    departures = []
    count = 0
    for departure in all_departures:
        if count < max_list_size:
            departures.append(DepartureInfo(
                departure['lt4:std'],
                departure['lt4:etd'],
                departure['lt4:operator'],
                departure['lt5:destination']['lt4:location']['lt4:locationName'],
                in_past=False,
                live=True
            ))
            count += 1
        else:
            break
    return departures


def parse_fastest_departure_soap_response(response):
    departure_board = None
    try:
        raw_dict = xmltodict.parse(response)
        departure_board = raw_dict['soap:Envelope']['soap:Body']['GetFastestDeparturesResponse']['DeparturesBoard']
    except (KeyError, Exception):
        handle_soap_fault(response)

    # Make sure there is at least one service available
    departure = departure_board['lt5:departures']['lt5:destination']['lt5:service']
    if '@xsi:nil' in departure:
        logger.warning('OpenLDBWS returned no departures')
        return None

    return DepartureInfo(
        departure['lt4:std'],
        departure['lt4:etd'],
        departure['lt4:operator'],
        departure['lt5:destination']['lt4:location']['lt4:locationName'],
        in_past=False,
        live=True
    )


def handle_soap_fault(response):
    try:
        raw_dict = xmltodict.parse(response)

        fault = raw_dict['soap:Envelope']['soap:Body']['soap:Fault']
        cause = str(fault['soap:Code']['soap:Value'])
        reason = str(fault['soap:Reason']['soap:Text']['#text'])
    except (KeyError, Exception):
        logger.error('OpenLDBWS failed for unknown reason')
        raise OpenLDBWSError('Request to Darwin failed - Could not parse response.')

    if cause == 'soap:Sender':
        logger.error('OpenLDBWS rejected request')
        raise ApplicationError('Request to Darwin failed - ' + reason)
    else:
        logger.error('OpenLDBWS responded in an unexpected way')
        raise OpenLDBWSError('Request to Darwin failed - ' + reason)
