import json
import re

trainees_db = []

# تعبير نمطي لمنع هجمات الحقن (SQLi / XSS Injection Controls)
SAFE_TEXT_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-_@.]{2,50}$")
EMAIL_PATTERN = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

# إعدادات CORS للسماح للفرونت إند (CloudFront) بالاتصال بالباك إند
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
        if not SAFE_TEXT_PATTERN.match(data[field]):
            return False, f"Security Alert: Potential injection detected in '{field}'!"
    
    if not EMAIL_PATTERN.match(data['email']):
        return False, "Invalid email format"
        
    return True, "Valid"

def lambda_handler(event, context):
    http_method = event.get('httpMethod', 'POST')
    
    # الرد على طلبات الفحص المسبق من المتصفح (CORS Preflight)
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'status': 'OK'})}

    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    user_role = claims.get('cognito:groups', 'Trainee')

    # مسار عرض المتدربين (GET)
    if http_method == 'GET':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'trainees': trainees_db, 'role': user_role})
        }

    # مسار تسجيل متدرب جديد (POST)
    if http_method == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
        except Exception:
            return {'statusCode': 400, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Malformed JSON payload'})}

        is_valid, message = validate_input(body)
        if not is_valid:
            return {'statusCode': 400, 'headers': CORS_HEADERS, 'body': json.dumps({'error': message})}

        new_trainee = {
            'id': len(trainees_db) + 1,
            'name': body['name'],
            'email': body['email'],
            'track': body['track']
        }
        trainees_db.append(new_trainee)

        return {
            'statusCode': 201,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'message': 'Trainee registered securely!',
                'trainee': new_trainee
            })
        }

    return {'statusCode': 405, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Method Not Allowed'})}