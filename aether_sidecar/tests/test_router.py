from aether_sidecar.models import Subsystem
from aether_sidecar.router import detect_subsystem_alerts, is_minecraft_related, subsystem_teaching_context


def test_subsystem_teaching_context_includes_purpose_and_keywords():
    context = subsystem_teaching_context(Subsystem.HELIOS)

    assert "Helios focus:" in context
    assert "energy systems" in context
    assert "Routing keywords to watch:" in context
    assert "power" in context


def test_detect_subsystem_alerts_uses_profile_keywords():
    alerts = detect_subsystem_alerts("The portal anomaly damaged the machine generator")

    assert alerts[Subsystem.ECLIPSE] == ["anomaly", "portal"]
    assert alerts[Subsystem.HELIOS] == ["machine", "generator"]


def test_is_minecraft_related_true_for_minecraft_context():
    assert is_minecraft_related("How do I improve my Minecraft modding workflow in NeoForge?")


def test_is_minecraft_related_false_for_smalltalk():
    assert not is_minecraft_related("How are you doing today?")
