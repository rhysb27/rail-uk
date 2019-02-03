import boto3
import logging
from rail_uk.dtos import Station, HomeStation
from rail_uk.exceptions import DynamoDBError


logger = logging.getLogger(__name__)


def set_home_station(user_id, home_station_details):

    db = boto3.resource('dynamodb', region_name='eu-west-1')
    table = db.Table('RailUK')

    existing_details = get_home_station(user_id)
    if existing_details is None:
        logger.info('Setting user\'s home station')
        response = table.put_item(
            Item={
                'UserID': user_id,
                'station_name': home_station_details.station.name,
                'station_crs': home_station_details.station.crs,
                'distance': home_station_details.distance
            }
        )
        logger.debug("DynamoDB PUT response: \n" + str(response))

        if _was_success(response):
            return "set"

        logger.error('DynamoDB failed to set home station')
        raise DynamoDBError('DynamoDB failed to set home station')
    else:
        logger.info('Updating user\'s home station')
        response = table.update_item(
            Key={
                'UserID': user_id
            },
            UpdateExpression='SET station_name = :station_name, station_crs = :station_crs, distance = :distance',
            ExpressionAttributeValues={
                ':station_name': home_station_details.station.name,
                ':station_crs': home_station_details.station.crs,
                ':distance': home_station_details.distance
            },
            ReturnValues="UPDATED_NEW"
        )
        logger.debug("DynamoDB UPDATE response: \n" + str(response))

        if _was_success(response):
            return "updated"

        logger.error('DynamoDB failed to update home station')
        raise DynamoDBError('DynamoDB failed to update home station')


def get_home_station(user_id):

    db = boto3.resource('dynamodb', region_name='eu-west-1')
    table = db.Table('RailUK')

    response = table.get_item(
        Key={
            'UserID': user_id
        }
    )
    logger.debug("DynamoDB GET response: \n" + str(response))

    if 'Item' not in response:
        logger.warning('DynamoDB returned no home station')
        return None

    details = response['Item']
    station = Station(details['station_name'], details['station_crs'])
    return HomeStation(station, int(details['distance']))


def _was_success(query_response):
    try:
        http_status = query_response['ResponseMetadata']['HTTPStatusCode']
        return http_status < 300
    except KeyError:
        return False
