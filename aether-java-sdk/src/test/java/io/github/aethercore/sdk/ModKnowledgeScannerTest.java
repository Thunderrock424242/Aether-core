package io.github.aethercore.sdk;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.jar.JarEntry;
import java.util.jar.JarOutputStream;
import org.junit.jupiter.api.Test;

class ModKnowledgeScannerTest {

    @Test
    void scansJarAndBuildsPerSubsystemKnowledge() throws IOException {
        Path tempDir = Files.createTempDirectory("aether-mod-scan-test");
        Path modsDir = tempDir.resolve("mods");
        Files.createDirectories(modsDir);
        Path jarPath = modsDir.resolve("example-mod.jar");

        try (JarOutputStream out = new JarOutputStream(Files.newOutputStream(jarPath))) {
            out.putNextEntry(new JarEntry("META-INF/mods.toml"));
            out.write("modLoader=\"javafml\"".getBytes());
            out.closeEntry();

            out.putNextEntry(new JarEntry("com/example/ExampleFeature.class"));
            out.write(new byte[] {0x01, 0x02, 0x03});
            out.closeEntry();
        }

        HostingConfig config = new HostingConfig(
                true,
                true,
                true,
                "http://127.0.0.1:8765",
                List.of("echo", "start"),
                Path.of("."),
                true,
                List.of(modsDir),
                Map.of(
                        "Sentinel", "General strategy guidance",
                        "Builder", "Construction and progression tips"
                )
        );

        ModKnowledgeScanner scanner = new ModKnowledgeScanner();
        List<SubsystemKnowledgeIndex> indexes = scanner.scan(config);

        assertFalse(indexes.isEmpty());
        assertTrue(indexes.stream().anyMatch(i -> i.subsystem().equals("Sentinel")));
        assertTrue(indexes.stream().anyMatch(i -> i.subsystem().equals("Builder")));
        assertTrue(indexes.stream().allMatch(i -> !i.entries().isEmpty()));
    }
}
