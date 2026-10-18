import json
import re

# قائمة محاكاة لقاعدة البيانات
trainees_db = []

# تعبير نمطي (Regex) لمنع أي محاولات حقن خبيثة (SQLi / XSS Injection Controls)
SAFE_TEXT_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-_@.]{2,50}$")
EMAIL_PATTERN = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

def validate_input(data):
    """التحقق الصارم من المدخلات لمنع هجمات الحقن (Input Validation)"""
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
    """الدالة الرئيسية التي تعمل على AWS Lambda خلف API Gateway"""
    
    # 1. استخراج طريقة الطلب (GET أو POST) ومعلومات الهوية من Cognito (RBAC/ABAC)
    http_method = event.get('httpMethod', 'POST')
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    user_role = claims.get('cognito:groups', 'Trainee')
    user_department = claims.get('custom:department', 'General') # ABAC Attribute

    # 2. تطبيق RBAC/ABAC: مسار عرض المتدربين مسموح فقط للـ Admin
    if http_method == 'GET':
        if 'Admin' not in str(user_role):
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Access Denied: RBAC policy requires Admin role'})
            }
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'trainees': trainees_db, 'department_scope': user_department})
        }

    # 3. مسار تسجيل متدرب جديد (POST /register) مع فحص المدخلات
    if http_method == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
        except Exception:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Malformed JSON payload'})}

        is_valid, message = validate_input(body)
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': message})
            }

        new_trainee = {
            'id': len(trainees_db) + 1,
            'name': body['name'],
            'email': body['email'],
            'track': body['track']
        }
        trainees_db.append(new_trainee)

        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Trainee registered securely via Serverless API!',
                'trainee_id': new_trainee['id']
            })
        }

    return {'statusCode': 405, 'body': json.dumps({'error': 'Method Not Allowed'})}