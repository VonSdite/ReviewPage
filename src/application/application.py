#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""应用装配入口。"""

from __future__ import annotations

import atexit
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .app_context import AppContext
from ..config import ConfigManager
from ..integrations import build_configured_agents, build_configured_hubs, register_builtin_integrations
from ..presentation import WebController, create_flask_app
from ..repositories import ReviewRepository
from ..services import ReviewQueueWorker, ReviewService
from ..utils import create_connection_factory


class Application:
    """负责装配 Review Page 的运行组件。"""

    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._root_path = Path(__file__).resolve().parents[2]
        self._flask_app = create_flask_app()

        self._setup_config()
        self._setup_logging()
        self._setup_context()
        self._setup_repositories()
        self._setup_integrations()
        self._setup_services()
        self._setup_controllers()
        self._setup_shutdown_hook()

        self._logger.info("Review Page initialized successfully")

    def _setup_config(self) -> None:
        self._config_manager = ConfigManager(self._config_path, self._root_path)

    def _setup_logging(self) -> None:
        log_dir = Path(self._config_manager.get_log_path())
        log_dir.mkdir(parents=True, exist_ok=True)
        level_name = self._config_manager.get_log_level()
        level = getattr(logging, level_name.upper(), logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s|%(name)s|%(filename)s:%(lineno)d|%(levelname)s|%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        logger = logging.getLogger("review_page")
        logger.handlers.clear()
        logger.setLevel(level)

        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

        self._logger = logger
        self._flask_app.logger = logger

    def _setup_context(self) -> None:
        self._ctx = AppContext(
            logger=self._logger,
            config_manager=self._config_manager,
            root_path=self._root_path,
            flask_app=self._flask_app,
        )

    def _setup_repositories(self) -> None:
        db_path = Path(self._config_manager.get_database_path())
        self._db_connection_factory = create_connection_factory(db_path)
        self._review_repository = ReviewRepository(self._db_connection_factory)

    def _setup_integrations(self) -> None:
        register_builtin_integrations()

        self._agents = build_configured_agents(self._ctx)
        self._hubs = build_configured_hubs(self._ctx)

        self._logger.info(
            "Registered integrations loaded: agents=%s hubs=%s",
            sorted(self._agents),
            sorted(self._hubs),
        )

    def _setup_services(self) -> None:
        self._review_service = ReviewService(
            self._ctx,
            review_repository=self._review_repository,
            agents=self._agents,
            hubs=self._hubs,
        )
        self._queue_worker = ReviewQueueWorker(
            self._ctx,
            review_service=self._review_service,
            poll_interval_seconds=self._config_manager.get_queue_poll_interval_seconds(),
        )
        self._queue_worker.start()

    def _setup_controllers(self) -> None:
        self._web_controller = WebController(
            self._ctx,
            review_service=self._review_service,
            queue_worker=self._queue_worker,
        )

    def _setup_shutdown_hook(self) -> None:
        atexit.register(self._queue_worker.stop)

    def run(self) -> None:
        host = self._config_manager.get_server_host()
        port = self._config_manager.get_server_port()

        try:
            from gevent.pywsgi import WSGIServer
        except ImportError:
            self._logger.warning("gevent not installed, fallback to Flask development server")
            self._flask_app.run(host=host, port=port, debug=False)
            return

        self._logger.info("Starting Review Page on %s:%s", host, port)
        server = WSGIServer((host, port), self._flask_app)
        server.serve_forever()
