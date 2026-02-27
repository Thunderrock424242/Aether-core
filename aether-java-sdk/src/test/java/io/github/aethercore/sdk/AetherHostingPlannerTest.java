package io.github.aethercore.sdk;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AetherHostingPlannerTest {

    @Test
    void prefersDedicatedServerWhenClientRole() {
        HostingConfig config = config(true, true, true);
        HostingDecision decision = AetherHostingPlanner.decide(HostingRole.CLIENT, config);
        assertEquals(HostingDecision.USE_DEDICATED_SERVER, decision);
    }

    @Test
    void hostsLocallyOnDedicatedServerWhenPreferred() {
        HostingConfig config = config(true, true, true);
        HostingDecision decision = AetherHostingPlanner.decide(HostingRole.DEDICATED_SERVER, config);
        assertEquals(HostingDecision.HOST_LOCALLY, decision);
    }

    @Test
    void doesNotHostWhenDisabled() {
        HostingConfig config = config(false, true, true);
        HostingDecision decision = AetherHostingPlanner.decide(HostingRole.DEDICATED_SERVER, config);
        assertEquals(HostingDecision.DO_NOT_HOST, decision);
    }

    private static HostingConfig config(boolean hostingEnabled, boolean autoStartEnabled, boolean preferDedicatedServer) {
        return new HostingConfig(
                hostingEnabled,
                autoStartEnabled,
                preferDedicatedServer,
                "http://127.0.0.1:8765",
                List.of("echo", "start"),
                Path.of("."),
                false,
                List.of(Path.of("mods")),
                Map.of()
        );
    }
}
