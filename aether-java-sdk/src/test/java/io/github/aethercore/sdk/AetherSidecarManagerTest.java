package io.github.aethercore.sdk;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AetherSidecarManagerTest {

    @Test
    void autoModeFallsBackToDedicatedWhenLocalRuntimeUnavailable() throws Exception {
        AetherSidecarManager manager = new AetherSidecarManager();
        HostingConfig config = config(BackendMode.AUTO);

        String selectedBaseUrl = manager.ensureHosting(HostingRole.DEDICATED_SERVER, config);

        assertEquals("http://example.invalid:8765", selectedBaseUrl);
    }

    @Test
    void localModeRaisesHelpfulErrorWhenLocalRuntimeUnavailable() {
        AetherSidecarManager manager = new AetherSidecarManager();
        HostingConfig config = config(BackendMode.LOCAL);

        AetherRuntimeUnavailableException exception = assertThrows(
                AetherRuntimeUnavailableException.class,
                () -> manager.ensureHosting(HostingRole.DEDICATED_SERVER, config));

        assertEquals(
                "Local A.E.T.H.E.R runtime is required but unavailable at http://127.0.0.1:1. Install/start the companion runtime (includes Ollama), then retry. Setup guide: https://ollama.com/download",
                exception.getMessage());
    }

    private static HostingConfig config(BackendMode backendMode) {
        return new HostingConfig(
                true,
                false,
                backendMode,
                "http://127.0.0.1:1",
                true,
                "http://example.invalid:8765",
                "https://ollama.com/download",
                List.of("echo", "start"),
                Path.of("."),
                false,
                List.of(Path.of("mods")),
                Map.of());
    }
}
