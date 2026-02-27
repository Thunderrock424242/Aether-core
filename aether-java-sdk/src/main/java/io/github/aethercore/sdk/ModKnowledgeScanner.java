package io.github.aethercore.sdk;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.jar.JarFile;
import java.util.stream.Collectors;

/**
 * Scans Minecraft mod folders/jars and builds per-subsystem local knowledge entries.
 */
public final class ModKnowledgeScanner {
    private static final int MAX_ENTRIES_PER_JAR = 200;

    public List<SubsystemKnowledgeIndex> scan(HostingConfig config) throws IOException {
        Objects.requireNonNull(config, "config");

        if (!config.modKnowledgeScanEnabled()) {
            return List.of();
        }

        List<ModKnowledgeEntry> discovered = discoverModEntries(config.modKnowledgeScanRoots());
        if (discovered.isEmpty()) {
            return List.of();
        }

        Map<String, String> objectives = config.subsystemObjectives();
        if (objectives.isEmpty()) {
            return List.of(new SubsystemKnowledgeIndex("default", "General Minecraft mod context", discovered));
        }

        return objectives.entrySet().stream()
                .map(entry -> new SubsystemKnowledgeIndex(entry.getKey(), entry.getValue(), discovered))
                .collect(Collectors.toList());
    }

    private List<ModKnowledgeEntry> discoverModEntries(List<Path> roots) throws IOException {
        List<ModKnowledgeEntry> entries = new ArrayList<>();
        for (Path root : roots) {
            if (root == null || !Files.exists(root)) {
                continue;
            }

            try (var stream = Files.walk(root)) {
                List<Path> paths = stream
                        .filter(Files::isRegularFile)
                        .sorted(Comparator.comparing(Path::toString))
                        .collect(Collectors.toList());

                for (Path file : paths) {
                    String name = file.getFileName().toString();
                    if (name.endsWith(".jar")) {
                        entries.addAll(scanJar(file));
                    } else if (name.endsWith(".toml") || name.endsWith(".json") || name.endsWith(".mcmeta")) {
                        entries.add(new ModKnowledgeEntry(file.toString(), "config-file:" + name));
                    }
                }
            }
        }
        return entries;
    }

    private List<ModKnowledgeEntry> scanJar(Path jarPath) throws IOException {
        List<ModKnowledgeEntry> entries = new ArrayList<>();
        try (JarFile jarFile = new JarFile(jarPath.toFile())) {
            var jarEntries = jarFile.stream()
                    .filter(e -> !e.isDirectory())
                    .map(e -> e.getName())
                    .filter(name -> name.endsWith(".class") || name.endsWith("mods.toml") || name.endsWith("pack.mcmeta") || name.endsWith(".json"))
                    .limit(MAX_ENTRIES_PER_JAR)
                    .collect(Collectors.toList());

            for (String entry : jarEntries) {
                entries.add(new ModKnowledgeEntry(jarPath.toString(), entry));
            }
        }
        return entries;
    }
}
