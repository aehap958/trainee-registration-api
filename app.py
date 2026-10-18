from flask import Flask, request, jsonify

app = Flask(__name__)
trainees_db = []

@app.route('/register', methods=['POST'])
def register_trainee():
    data = request.get_json()
    if not data or 'name' not in data or 'email' not in data or 'track' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    new_trainee = {
        "id": len(trainees_db) + 1,
        "name": data['name'],
        "email": data['email'],
        "track": data['track']
    }
    trainees_db.append(new_trainee)
    return jsonify({"message": "Trainee registered successfully!", "trainee_id": new_trainee['id']}), 201

if __name__ == '__main__':
app.run(debug=False)