import boto3
import json
import logging
import os
import base64

from botocore.exceptions import ClientError
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_secret():

    secret_name = "SlackWebHookURL"
    region_name = "eu-west-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return secret
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            return decoded_binary_secret

SLACK_CHANNEL = os.environ['slackChannel']
secret = json.loads(get_secret())
HOOK_URL = "https://" + secret['SlackWebhookURL']


def lambda_handler(event, context):
    logger.info("Event: " + str(event))
    message = json.loads(event['Records'][0]['Sns']['Message'])
    logger.info("Message: " + str(message))

    alarmName = message['AlarmName']
    newState = message['NewStateValue']
    reason = message['NewStateReason']
    metricName = message['Trigger']['MetricName']
   
#Set Slack Message colour based on alarm state
    messageColor = ''
    if (newState == 'OK'):
        messageColor = 'good'
    elif (newState == 'ALARM'):
        messageColor = 'danger'
    else:
        messageColor = 'good'

#Prepare request body which will be sent to slack API
    slackMessage = {
        'channel': SLACK_CHANNEL,
        'text': '*CloudWatchAlarm*',
        'attachments': [
            {
                'text': '*AlarmName* : {} \n*NewState* : {} \n*MetricName* : {} \n*Reason* : {}'.format(alarmName, newState, metricName, reason),
                'color': messageColor
            }
        ]

    }

    req = Request(HOOK_URL, json.dumps(slackMessage).encode('utf-8'))
    try:
        response = urlopen(req)
        response.read()
        logger.info("Message posted to %s", slackMessage['channel'])
    except HTTPError as e:
        logger.error("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        logger.error("Server connection failed: %s", e.reason)