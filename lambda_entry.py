from rail_uk.lambda_handler import lambda_handler


def lambda_entry(event, context):
    """Wrap the main lambda handler, so that all functionality can be
    tested while maintaining an entry point in the root of the project,
    as per AWS Lambda's requirements.
    """
    return lambda_handler(event, context)
