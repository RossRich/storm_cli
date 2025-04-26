#!/bin/python3

from flask import Flask
from flask import render_template
from flask_socketio import SocketIO
from modules.model import Model
from modules.presenter import Presenter
from modules.serial_worker import SerialWorker
from modules.socket_worker import SocketView
from modules.view import View
from static_data import Templates

app = Flask(__name__)

@app.errorhandler(500)
def no_serial(error) -> str:
  return render_template(Templates.no_serial), 500


@app.route("/")
def home() -> str:
  return render_template(Templates.index)


if __name__ == "__main__":
  app.config["SECRET_KEY"] = "secret!"
  socketio = SocketIO(app)
  model = Model()
  socket_ns = SocketView("/")
  view = View(socket_ns)
  socketio.on_namespace(socket_ns)
  sw = SerialWorker(120)
  sw.verbose = False
  presenter = Presenter(view, model, sw)
  presenter.verbose = True
  sw.begin()
  app.run(debug=True)
  sw.end()
  print("DONE!")
