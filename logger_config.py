import logging
from pathlib import Path


def setup_logger(name: str = "LoanRiskMAS") -> logging.Logger:
    Path("logs").mkdir(exist_ok=True)
    _logger = logging.getLogger(name)
    _logger.setLevel(logging.DEBUG)
    if _logger.handlers:
        return _logger
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler("logs/agent_run.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    _logger.addHandler(fh)
    _logger.addHandler(ch)
    return _logger


logger = setup_logger()
