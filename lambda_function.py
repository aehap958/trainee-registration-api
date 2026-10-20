import json
import re
import uuid
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
TABLE_NAME = 'TraineesTable-ahmedehab'
table = dynamodb.Table(TABLE_NAME)

SAFE_TEXT_PATTERN = re.compile(r"^[\u0600-\u06FFa-zA-Z0-9\s\-_@.&/()]{2,80}$")
EMAIL_PATTERN = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

def lambda_handler(event, context):
    # قراءة نوع الطلب سواء جاي من Function URL أو API Gateway
    http_method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod', 'GET')
    
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'body': json.dumps({'status': 'ok'})}

    if http_method == 'GET':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'ok', 'message': 'Server is online'})
        }

    if http_method == 'POST':
        try:
            raw_body = event.get('body') or '{}'
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            name = str(body.get('name', '')).strip()
            email = str(body.get('email', '')).strip().lower()
            track = str(body.get('track', '')).strip()

            if not name or not email or not track:
                return {'statusCode': 400, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'error': 'Missing fields'})}

            trainee_id = f"TR-{str(uuid.uuid4())[:8].upper()}"
            new_trainee = {
                'email': email,
                'id': trainee_id,
                'trainee_id': trainee_id,
                'name': name,
                'track': track,
                'created_at': datetime.utcnow().isoformat()
            }

            try:
                table.put_item(Item=new_trainee, ConditionExpression='attribute_not_exists(email)')
            except ClientError as e:
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    return {'statusCode': 409, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'error': 'هذا البريد الإلكتروني مسجل مسبقاً!'})}
            except Exception as db_err:
                print(f"DB Warning: {db_err}")

            return {
                'statusCode': 201,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'message': 'Registered successfully!',
                    'id': trainee_id,
                    'trainee_id': trainee_id,
                    'trainee': new_trainee
                })
            }
        except Exception as e:
            return {'statusCode': 500, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'error': str(e)})}

    return {'statusCode': 200, 'body': json.dumps({'status': 'ok'})}