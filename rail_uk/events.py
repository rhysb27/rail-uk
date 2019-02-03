import logging

from rail_uk.intents import get_next_train, get_fastest_train, get_last_train, set_home_station, get_welcome_response, \
    handle_session_end_request, get_error_response, get_api_error_response, get_db_error_response
from rail_uk.exceptions import ApplicationError, OpenLDBWSError, TransportAPIError, DynamoDBError

logger = logging.getLogger(__name__)


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
    try:
        if intent_name == "NextTrain":
            logger.info('NextTrain Intent: ' + session['sessionId'])
            return get_next_train(intent, session)
        elif intent_name == "FastestTrain":
            logger.info('FastestTrain Intent: ' + session['sessionId'])
            return get_fastest_train(intent, session)
        elif intent_name == "LastTrain":
            logger.info('LastTrain Intent: ' + session['sessionId'])
            return get_last_train(intent, session)
        elif intent_name == "SetHomeStation":
            logger.info('SetHomeStation Intent: ' + session['sessionId'])
            return set_home_station(intent, session)
        elif intent_name == "AMAZON.HelpIntent":
            logger.info('HelpIntent: ' + session['sessionId'])
            return get_welcome_response()
        elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
            logger.info('{}: {}'.format(intent_name, session['sessionId']))
            return handle_session_end_request()
        else:
            logger.error('Invalid intent provided')
            raise ValueError("Invalid intent")

    except (OpenLDBWSError, TransportAPIError):
        logger.exception('-[API ERROR]- Underlying API failed:')
        return get_api_error_response()

    except DynamoDBError:
        logger.exception('-[DYNAMODB ERROR]- DynamoDB failed to set/update user details:')
        return get_db_error_response()

    except (ApplicationError, Exception):
        logger.exception('-[RAIL UK ERROR]- Rail UK ran into an exception:')
        return get_error_response()
