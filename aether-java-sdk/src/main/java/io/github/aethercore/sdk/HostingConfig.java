package io.github.aethercore.sdk;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Configures if/where A.E.T.H.E.R hosting should run for JVM integrations.
 */
public final class HostingConfig {
    private final boolean hostingEnabled;
    private final boolean autoStartEnabled;
    private final BackendMode backendMode;
    private final String localSidecarBaseUrl;
    private final boolean preferDedicatedServer;
    private final String dedicatedServerBaseUrl;
    private final String runtimeInstallHelpUrl;
    private final List<String> sidecarStartCommand;
    private final Path sidecarWorkingDirectory;
    private final boolean modKnowledgeScanEnabled;
    private final List<Path> modKnowledgeScanRoots;
    private final Map<String, String> subsystemObjectives;

    public HostingConfig(
            boolean hostingEnabled,
            boolean autoStartEnabled,
            BackendMode backendMode,
            String localSidecarBaseUrl,
            boolean preferDedicatedServer,
            String dedicatedServerBaseUrl,
            String runtimeInstallHelpUrl,
            List<String> sidecarStartCommand,
            Path sidecarWorkingDirectory,
            boolean modKnowledgeScanEnabled,
            List<Path> modKnowledgeScanRoots,
            Map<String, String> subsystemObjectives
    ) {
        this.hostingEnabled = hostingEnabled;
        this.autoStartEnabled = autoStartEnabled;
        this.backendMode = backendMode == null ? BackendMode.AUTO : backendMode;
        this.localSidecarBaseUrl = Objects.requireNonNull(localSidecarBaseUrl, "localSidecarBaseUrl");
        this.preferDedicatedServer = preferDedicatedServer;
        this.dedicatedServerBaseUrl = Objects.requireNonNull(dedicatedServerBaseUrl, "dedicatedServerBaseUrl");
        this.runtimeInstallHelpUrl = runtimeInstallHelpUrl == null ? "" : runtimeInstallHelpUrl;
        this.sidecarStartCommand = List.copyOf(Objects.requireNonNull(sidecarStartCommand, "sidecarStartCommand"));
        this.sidecarWorkingDirectory = Objects.requireNonNull(sidecarWorkingDirectory, "sidecarWorkingDirectory");
        this.modKnowledgeScanEnabled = modKnowledgeScanEnabled;
        this.modKnowledgeScanRoots = List.copyOf(Objects.requireNonNull(modKnowledgeScanRoots, "modKnowledgeScanRoots"));
        this.subsystemObjectives = Map.copyOf(Objects.requireNonNull(subsystemObjectives, "subsystemObjectives"));
    }

    public static HostingConfig defaults() {
        return new HostingConfig(
                false,
                true,
                BackendMode.AUTO,
                "http://127.0.0.1:8765",
                true,
                "http://127.0.0.1:8765",
                "https://ollama.com/download",
                List.of("./scripts/run_sidecar_dev.sh"),
                Path.of("."),
                false,
                List.of(Path.of("mods")),
                Map.of()
        );
    }

    public boolean hostingEnabled() {
        return hostingEnabled;
    }

    public boolean autoStartEnabled() {
        return autoStartEnabled;
    }

    public BackendMode backendMode() {
        return backendMode;
    }

    public String localSidecarBaseUrl() {
        return localSidecarBaseUrl;
    }

    public boolean preferDedicatedServer() {
        return preferDedicatedServer;
    }

    public String dedicatedServerBaseUrl() {
        return dedicatedServerBaseUrl;
    }

    public String runtimeInstallHelpUrl() {
        return runtimeInstallHelpUrl;
    }

    public List<String> sidecarStartCommand() {
        return sidecarStartCommand;
    }

    public Path sidecarWorkingDirectory() {
        return sidecarWorkingDirectory;
    }

    public boolean modKnowledgeScanEnabled() {
        return modKnowledgeScanEnabled;
    }

    public List<Path> modKnowledgeScanRoots() {
        return modKnowledgeScanRoots;
    }

    public Map<String, String> subsystemObjectives() {
        return subsystemObjectives;
    }
}
