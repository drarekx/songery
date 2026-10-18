"""Punt d'entrada (desenvolupament): python app.py [--port 8000] [--host 127.0.0.1] [--debug] [--sense-recarrega]

Es torna a carregar sol quan canvia el codi Python (o una plantilla), perquè el servidor no es quedi
executant codi antic amb plantilles noves. L'app d'escriptori (escriptori.py) no ho fa.
"""

import argparse

from canconer.web import crea_app

app = crea_app()

if __name__ == "__main__":
    arguments = argparse.ArgumentParser(description="Generador de cançoners en llibret A5")
    arguments.add_argument("--host", default="127.0.0.1",
                           help="0.0.0.0 per obrir-lo des del mòbil a la mateixa xarxa")
    arguments.add_argument("--port", type=int, default=5050)
    arguments.add_argument("--debug", action="store_true", help="depurador de Flask (només en local!)")
    arguments.add_argument("--sense-recarrega", action="store_true",
                           help="no tornar a carregar el servidor quan canvia el codi")
    a = arguments.parse_args()
    app.jinja_env.auto_reload = True
    app.run(host=a.host, port=a.port, debug=a.debug, use_reloader=not a.sense_recarrega)
