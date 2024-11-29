#!/bin/python3

import serial
from flask import Flask, url_for
from flask import render_template
from flask_socketio import SocketIO

current = list(range(0, 70))
thirst = []

app = Flask(__name__)
app.config["SECRET_KEY"] ="secret!"
socketio = SocketIO(app)

@socketio.on('message')
def handle_message(data):
  print('received message: ' + data)

@socketio.on('my event')
def handle_my_custom_event(json):
    print('received json: ' + str(json))

@app.route("/")
def home() -> str:
  a = url_for('static', filename='css/materialize.min.css')
  print(a)
  return render_template("index.html", )

if __name__ == "__main__":
  socketio.run(app)