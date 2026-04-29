package io.github.aethercore.sdk;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.StringJoiner;
import java.util.function.Consumer;
import java.util.jar.JarFile;
import java.util.stream.Collectors;

/**
 * Scans Minecraft mod folders/jars and builds per-subsystem local knowledge entries.
 */
public final class ModKnowledgeScanner {
    private static final int MAX_ENTRIES_PER_JAR = 200;
    private String lastFingerprint;
    private List<SubsystemKnowledgeIndex> cachedIndexes = List.of();

    public List<SubsystemKnowledgeIndex> scan(HostingConfig config) throws IOException {
        return scanWithProgress(config, null).indexes();
    }

    /**
     * Scans configured mod roots and emits progress updates that can be wired to a menu progress bar.
     * Reuses cached data when no file-level changes are detected.
     */
    public ModKnowledgeScanResult scanWithProgress(HostingConfig config, Consumer<ModKnowledgeScanProgress> progressListener)
            throws IOException {
        Objects.requireNonNull(config, "config");

        if (!config.modKnowledgeScanEnabled()) {
            notifyProgress(progressListener, new ModKnowledgeScanProgress(0, 0, true, false, "Mod scan disabled"));
            return new ModKnowledgeScanResult(List.of(), false);
        }

        List<Path> files = collectCandidateFiles(config.modKnowledgeScanRoots());
        String fingerprint = buildFingerprint(files);
        if (fingerprint.equals(lastFingerprint) && !cachedIndexes.isEmpty()) {
            notifyProgress(progressListener, new ModKnowledgeScanProgress(files.size(), files.size(), true, true,
                    "Mod knowledge ready from cache"));
            return new ModKnowledgeScanResult(cachedIndexes, true);
        }

        List<ModKnowledgeEntry> discovered = discoverModEntries(files, progressListener);
        if (discovered.isEmpty()) {
            notifyProgress(progressListener, new ModKnowledgeScanProgress(files.size(), files.size(), true, false,
                    "No supported mod knowledge sources found"));
            return new ModKnowledgeScanResult(List.of(), false);
        }

        Map<String, String> objectives = config.subsystemObjectives();
        List<SubsystemKnowledgeIndex> indexes;
        if (objectives.isEmpty()) {
            indexes = List.of(new SubsystemKnowledgeIndex("default", "General Minecraft mod context", discovered));
        } else {
            indexes = objectives.entrySet().stream()
                .map(entry -> new SubsystemKnowledgeIndex(entry.getKey(), entry.getValue(), discovered))
                .collect(Collectors.toList());
        }

        this.lastFingerprint = fingerprint;
        this.cachedIndexes = List.copyOf(indexes);
        notifyProgress(progressListener, new ModKnowledgeScanProgress(files.size(), files.size(), true, false,
                "Mod knowledge scan complete"));
        return new ModKnowledgeScanResult(indexes, false);
    }

    private List<Path> collectCandidateFiles(List<Path> roots) throws IOException {
        List<Path> paths = new ArrayList<>();
        for (Path root : roots) {
            if (root == null || !Files.exists(root)) {
                continue;
            }

            try (var stream = Files.walk(root)) {
                paths.addAll(stream
                        .filter(Files::isRegularFile)
                        .filter(this::isSupportedFile)
                        .sorted(Comparator.comparing(Path::toString))
                        .collect(Collectors.toList()));
            }
        }
        return paths;
    }

    private String buildFingerprint(List<Path> files) throws IOException {
        StringJoiner joiner = new StringJoiner("|");
        for (Path file : files) {
            joiner.add(file.toString() + "#" + Files.size(file) + "#" + Files.getLastModifiedTime(file).toMillis());
        }
        return joiner.toString();
    }

    private List<ModKnowledgeEntry> discoverModEntries(List<Path> paths, Consumer<ModKnowledgeScanProgress> progressListener)
            throws IOException {
        List<ModKnowledgeEntry> entries = new ArrayList<>();
        int total = paths.size();
        int processed = 0;
        for (Path file : paths) {
            String name = file.getFileName().toString();
            if (name.endsWith(".jar")) {
                entries.addAll(scanJar(file));
            } else if (name.endsWith(".toml") || name.endsWith(".json") || name.endsWith(".mcmeta")) {
                entries.add(new ModKnowledgeEntry(file.toString(), "config-file:" + name));
            }
            processed++;
            notifyProgress(progressListener, new ModKnowledgeScanProgress(total, processed, processed == total, false,
                    "Scanning " + name));
        }
        return entries;
    }

    private boolean isSupportedFile(Path file) {
        String name = file.getFileName().toString();
        return name.endsWith(".jar") || name.endsWith(".toml") || name.endsWith(".json") || name.endsWith(".mcmeta");
    }

    private void notifyProgress(Consumer<ModKnowledgeScanProgress> progressListener, ModKnowledgeScanProgress progress) {
        if (progressListener != null) {
            progressListener.accept(progress);
        }
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
