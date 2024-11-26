#!/bin/python3

import serial
from flask import Flask, url_for
from flask import render_template



# url_for('static', filename='js/materialize.min.js')

app = Flask(__name__)
@app.route("/")
def home() -> str:
  a = url_for('static', filename='css/materialize.min.css')
  print(a)
  return render_template("index.html", )

# if __name__ == "__main__":
#   try:
#     main()
#   except Exception as e:
#     print(str(e))