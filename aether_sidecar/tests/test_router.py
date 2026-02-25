from aether_sidecar.models import Subsystem
from aether_sidecar.router import detect_subsystem_alerts, pick_subsystem


def test_pick_subsystem_anomaly():
    assert pick_subsystem("There is a rift anomaly by my base") == Subsystem.ECLIPSE


def test_pick_subsystem_default():
    assert pick_subsystem("hello") == Subsystem.AEGIS


def test_detect_subsystem_alerts_multiple_systems():
    alerts = detect_subsystem_alerts("rift anomaly near machine power core")
    assert Subsystem.ECLIPSE in alerts
    assert Subsystem.HELIOS in alerts
    assert "anomaly" in alerts[Subsystem.ECLIPSE]
    assert "power" in alerts[Subsystem.HELIOS]
