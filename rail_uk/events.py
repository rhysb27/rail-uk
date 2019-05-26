import logging
from os import environ

from rail_uk.intents import get_next_train, get_fastest_train, get_last_train, set_home_station, get_welcome_response, \
    handle_session_end_request, get_error_response, get_api_error_response, get_db_error_response, \
    get_station_not_found_response
from rail_uk.exceptions import ApplicationError, OpenLDBWSError, TransportAPIError, DynamoDBError, EntityResolutionError

logger = logging.getLogger(__name__)
logger.setLevel(level=environ.get('LOG_LEVEL', 'INFO'))


def on_launch(session):
    """ Called when the user launches the skill without specifying what they
    want
    """
    logger.info('Launched without intent: ' + session['sessionId'])
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user invokes an intent
    """
    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to skill's intent handlers
    logger.info('Accessing {} intent'.format(intent_name))

    try:
        if intent_name == 'NextTrain':
            return get_next_train(intent, session)
        elif intent_name == 'FastestTrain':
            return get_fastest_train(intent, session)
        elif intent_name == 'LastTrain':
            return get_last_train(intent, session)
        elif intent_name == 'SetHomeStation':
            return set_home_station(intent, session)
        elif intent_name == 'AMAZON.HelpIntent':
            return get_welcome_response()
        elif intent_name == 'AMAZON.CancelIntent' or intent_name == "AMAZON.StopIntent":
            return handle_session_end_request()
        else:
            logger.error('Invalid intent provided')
            raise ValueError('Invalid intent')

    except (OpenLDBWSError, TransportAPIError):
        logger.exception('-[API ERROR]- Upstream API failed:')
        return get_api_error_response()

    except DynamoDBError:
        logger.exception('-[DYNAMODB ERROR]- DynamoDB failed to set/update user details:')
        return get_db_error_response()

    except EntityResolutionError as err:
        logger.exception('-[ALEXA ERROR]- Alexa failed to resolve requested station:')
        return get_station_not_found_response(err)

    except (ApplicationError, Exception):
        logger.exception('-[RAIL UK ERROR]- Rail UK encountered an exception:')
        return get_error_response()
