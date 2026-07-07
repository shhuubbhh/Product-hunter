from typing import Dict, Type
from app.monitors.base import BaseMonitor
from app.monitors.amazon import AmazonMonitor
from app.monitors.flipkart import FlipkartMonitor
from app.monitors.blinkit import BlinkitMonitor
from app.monitors.zepto import ZeptoMonitor
from app.monitors.reliance_digital import RelianceDigitalMonitor
from app.monitors.croma import CromaMonitor
from app.monitors.vijay_sales import VijaySalesMonitor

MONITOR_REGISTRY: Dict[str, Type[BaseMonitor]] = {
    "amazon": AmazonMonitor,
    "flipkart": FlipkartMonitor,
    "blinkit": BlinkitMonitor,
    "zepto": ZeptoMonitor,
    "reliance_digital": RelianceDigitalMonitor,
    "croma": CromaMonitor,
    "vijay_sales": VijaySalesMonitor,
}

def get_monitor(name: str) -> BaseMonitor:
    """Returns an instance of the requested store monitor."""
    monitor_class = MONITOR_REGISTRY.get(name.lower())
    if not monitor_class:
        raise ValueError(f"No monitor found for store: {name}")
    return monitor_class()
