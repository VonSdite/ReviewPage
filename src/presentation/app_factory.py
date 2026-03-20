#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flask app 工厂。"""

from pathlib import Path

from flask import Flask


def create_flask_app() -> Flask:
    base_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
        static_url_path="/static",
    )
    app.config["JSON_AS_ASCII"] = False
    return app
