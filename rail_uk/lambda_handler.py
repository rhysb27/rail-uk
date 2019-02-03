from os import environ
import logging

from rail_uk.events import on_launch, on_intent

logger = logging.getLogger(__name__)
logging.basicConfig(level=environ.get('LOG_LEVEL', 'WARNING'))


def lambda_handler(event, _):
    """
    Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """

    # Prevent someone else from configuring a skill that sends requests to this function
    skill_id = environ['SKILL_ID']
    if event['session']['application']['applicationId'] != skill_id:
        logger.error('Invalid Application ID: ' + event['session']['application']['applicationId'])
        raise ValueError('Invalid Application ID')

    if event['session']['new']:
        logger.info('Session started: ' + event['session']['sessionId'])

    # Route to appropriate event handler
    if event['request']['type'] == 'LaunchRequest':
        response = on_launch(event['session'])
        return response
    elif event['request']['type'] == 'IntentRequest':
        response = on_intent(event['request'], event['session'])
        return response
    elif event['request']['type'] == 'SessionEndedRequest':
        logger.info('Session ended: ' + event['session']['sessionId'])
