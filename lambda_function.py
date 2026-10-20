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

# تعبير نمطي لمنع هجمات الحقن (SQLi / XSS Injection Controls) مع دعم العربي والإنجليزي
SAFE_TEXT_PATTERN = re.compile(r"^[\u0600-\u06FFa-zA-Z0-9\s\-_@.]{2,50}$")
EMAIL_PATTERN = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
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
    http_method = event.get('httpMethod', 'POST')
    
    # الرد على فحص المتصفح المسبق (CORS)
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'status': 'OK'})}

    # استخراج صلاحيات المستخدم من Cognito (إن وجدت)
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    user_role = claims.get('cognito:groups', 'Trainee')

    # مسار GET: فحص حالة الخادم أو عرض المتدربين
    if http_method == 'GET':
        try:
            response = table.scan()
            items = response.get('Items', [])
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({'status': 'ok', 'count': len(items), 'trainees': items, 'role': user_role})
            }
        except Exception:
            return {'statusCode': 500, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Database error'})}

    # مسار POST: تسجيل متدرب جديد في DynamoDB
    if http_method == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
        except Exception:
            return {'statusCode': 400, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Malformed JSON payload'})}

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
            # حفظ المتدرب في DynamoDB مع شرط عدم تكرار البريد الإلكتروني
            table.put_item(
                Item=new_trainee,
                ConditionExpression='attribute_not_exists(email)'
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return {
                    'statusCode': 409,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({'error': 'هذا البريد الإلكتروني مسجل مسبقاً!'})
                }
            return {'statusCode': 500, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Failed to save to database'})}

        return {
            'statusCode': 201,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'message': 'Trainee registered securely in DynamoDB!',
                'id': trainee_id,
                'trainee_id': trainee_id,
                'trainee': new_trainee
            })
        }

    return {'statusCode': 405, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Method Not Allowed'})}