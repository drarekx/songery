"""Punt d'entrada: python app.py [--port 8000] [--host 127.0.0.1]"""

import argparse

from canconer.web import crea_app

app = crea_app()

if __name__ == "__main__":
    arguments = argparse.ArgumentParser(description="Generador de cançoners en llibret A5")
    arguments.add_argument("--host", default="127.0.0.1",
                           help="0.0.0.0 per obrir-lo des del mòbil a la mateixa xarxa")
    arguments.add_argument("--port", type=int, default=5050)
    arguments.add_argument("--debug", action="store_true")
    a = arguments.parse_args()
    app.run(host=a.host, port=a.port, debug=a.debug)
