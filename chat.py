from flask import Flask, request, jsonify,session
import random
import json
import torch

import time

from flask_mysqldb import MySQL

from model import NeuralNet
from nltk_utils import bag_of_words, tokenize

app = Flask(__name__)
app.secret_key = 'xyzsdfg'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'movie_recommendation'
mysql = MySQL(app)
with open('intents.json', 'r') as json_data:
    intents = json.load(json_data)

FILE = "data.pth"
data = torch.load(FILE)

input_size = data["input_size"]
hidden_size = data["hidden_size"]
output_size = data["output_size"]
all_words = data['all_words']
tags = data['tags']
model_state = data["model_state"]

model = NeuralNet(input_size, hidden_size, output_size).to(torch.device('cpu'))
model.load_state_dict(model_state)
model.eval()

bot_name = "MRS"

def extract_name(message):
    words = message.lower().split()
    if "name" in words and "is" in words:
        name_index = words.index("name") + 2
        return words[name_index]
    elif "name" in words:
        name_index = words.index("name") + 1
        return words[name_index]
    else:
        return None

user_name = None
last_interaction_time = time.time()

def get_response(msg):
    global user_name, last_interaction_time

    # Update the last interaction time whenever a request is received
    last_interaction_time = time.time()

    sentence = tokenize(msg)
    X = bag_of_words(sentence, all_words)
    X = X.reshape(1, X.shape[0])
    X = torch.from_numpy(X).to(torch.device('cpu'))

    output = model(X)
    _, predicted = torch.max(output, dim=1)

    tag = tags[predicted.item()]

    probs = torch.softmax(output, dim=1)
    prob = probs[0][predicted.item()]
    if prob.item() > 0.75:
        for intent in intents['intents']:
            if tag == intent["tag"]:
                if tag == "greeting":
                    if 'Name' in session:
                        user_name = session['Name']
                        return random.choice(intent['responses']).replace("User_name", user_name)
                    else:
                        return "I couldn't extract your name. Please provide it in a clear manner."
                elif tag == "provide_name":
                    user_name = extract_name(msg)
                    if user_name:
                        session['Name'] = user_name  # Store the extracted name in the session
                        return intent["responses"][0].replace("{user_name}", user_name)
                    else:
                        return "I couldn't extract your name. Please provide it in a clear manner."
                else:
                    return random.choice(intent['responses'])

    return "I’m sorry, I’m still learning and don’t have the answer to your question right now. Could we explore a different topic or question? I’m eager to assist you in any way I can. 😊"


def check_inactivity():
    return time.time() - last_interaction_time > 60

@app.route('/predict', methods=['POST'])
def predict():
    global last_interaction_time
    message = request.json.get('message', '')

    # Get a response using the model
    response = get_response(message)

    # Check if the user's name is available in the session
    if 'Name' in session:
        user_name = session['Name']
        response = f"Hello, {user_name}! " + response

    # Update the last interaction time
    last_interaction_time = time.time()

    # Check for inactivity
    if check_inactivity():
        response += "\nIt seems like you've been away for a bit. We're going to end this conversation for now, but don't hesitate to reach out if you need any assistance in the future. Take care! 😊"

    return jsonify({'response': response})


if __name__ == '__main__':
    app.run(debug=True)