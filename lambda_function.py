import json
import re
import uuid
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# الاتصال بجدول DynamoDB في منطقة أيرلندا
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
TABLE_NAME = 'TraineesTable-ahmedehab'
table = dynamodb.Table(TABLE_NAME)

# السماح بالحروف العربي والإنجليزي والأرقام والمسافات والرموز العادية
SAFE_TEXT_PATTERN = re.compile(r"^[\u0600-\u06FFa-zA-Z0-9\s\-_@.&/()]{2,80}$")
EMAIL_PATTERN = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

# عناوين CORS كاملة لمنع حظر المتصفح
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def validate_input(data):
    required_fields = ['name', 'email', 'track']
    for field in required_fields:
        if field not in data or not isinstance(data[field], str):
            return False, f"Missing or invalid field: {field}"
        if not SAFE_TEXT_PATTERN.match(data[field].strip()):
            return False, f"Security Alert: Potential injection detected in '{field}'!"
    if not EMAIL_PATTERN.match(data['email'].strip()):
        return False, "Invalid email format"
    return True, "Valid"

def lambda_handler(event, context):
    try:
        http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method', 'POST')
        
        # 1. الرد الفوري على طلبات OPTIONS (CORS Preflight)
        if http_method == 'OPTIONS':
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'status': 'OK'})}

        # 2. الرد على طلبات GET
        if http_method == 'GET':
            items = []
            try:
                response = table.scan()
                items = response.get('Items', [])
            except Exception as db_err:
                print(f"DynamoDB scan warning: {db_err}")
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({'status': 'ok', 'count': len(items), 'trainees': items})
            }

        # 3. الرد على طلبات POST (تسجيل متدرب جديد)
        if http_method == 'POST':
            raw_body = event.get('body') or '{}'
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

            is_valid, message = validate_input(body)
            if not is_valid:
                return {'statusCode': 400, 'headers': CORS_HEADERS, 'body': json.dumps({'error': message})}

            email = body['email'].strip().lower()
            trainee_id = f"TR-{str(uuid.uuid4())[:8].upper()}"

            new_trainee = {
                'email': email,
                'id': trainee_id,
                'trainee_id': trainee_id,
                'name': body['name'].strip(),
                'track': body['track'].strip(),
                'created_at': datetime.utcnow().isoformat()
            }

            try:
                table.put_item(
                    Item=new_trainee,
                    ConditionExpression='attribute_not_exists(email)'
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    return {'statusCode': 409, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'هذا البريد الإلكتروني مسجل مسبقاً!'})}
                print(f"DynamoDB ClientError: {e}")
            except Exception as db_err:
                print(f"DynamoDB put_item warning: {db_err}")

            return {
                'statusCode': 201,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'message': 'Trainee registered securely!',
                    'id': trainee_id,
                    'trainee_id': trainee_id,
                    'trainee': new_trainee
                })
            }

        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'status': 'ok'})}

    except Exception as e:
        print(f"Unhandled server error: {e}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f"Server error: {str(e)}"})
        }