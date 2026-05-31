import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, Request

from app.core.config import settings


def configure_logging() -> None:
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        return record

    logging.setLogRecordFactory(record_factory)
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s trace_id=%(trace_id)s %(message)s",
    )


class TraceAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("trace_id", self.extra.get("trace_id", "-"))
        return msg, kwargs


def get_logger(name: str, trace_id: str = "-") -> TraceAdapter:
    return TraceAdapter(logging.getLogger(name), {"trace_id": trace_id})


def configure_observability(app: FastAPI) -> None:
    configure_logging()

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        logging.getLogger(__name__).debug("OpenTelemetry FastAPI instrumentation unavailable")

    @app.middleware("http")
    async def add_request_timing(request: Request, call_next: Callable):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["x-clarifi-duration-ms"] = str(duration_ms)
        return response


@contextmanager
def trace_workflow(name: str, metadata: dict[str, Any] | None = None):
    logger = get_logger("clarifi.workflow")
    start = time.perf_counter()
    logger.info("workflow.start name=%s metadata=%s", name, metadata or {})
    try:
        yield
        logger.info("workflow.finish name=%s duration_ms=%s", name, round((time.perf_counter() - start) * 1000, 2))
    except Exception:
        logger.exception("workflow.error name=%s", name)
        raise
