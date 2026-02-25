from aether_sidecar.models import Subsystem
from aether_sidecar.router import pick_subsystem


def test_pick_subsystem_anomaly():
    assert pick_subsystem("There is a rift anomaly by my base") == Subsystem.ECLIPSE


def test_pick_subsystem_default():
    assert pick_subsystem("hello") == Subsystem.AEGIS
