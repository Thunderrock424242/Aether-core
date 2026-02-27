package io.github.aethercore.sdk;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.Objects;

/**
 * Starts sidecar hosting when configured and returns the endpoint clients should use.
 */
public final class AetherSidecarManager {
    private Process process;
    private final ModKnowledgeScanner modKnowledgeScanner = new ModKnowledgeScanner();
    private List<SubsystemKnowledgeIndex> lastKnowledgeIndexes = List.of();

    public synchronized String ensureHosting(HostingRole role, HostingConfig config) throws IOException, InterruptedException {
        Objects.requireNonNull(role, "role");
        Objects.requireNonNull(config, "config");

        HostingDecision decision = AetherHostingPlanner.decide(role, config);
        if (decision == HostingDecision.DO_NOT_HOST) {
            return config.dedicatedServerBaseUrl();
        }

        if (decision == HostingDecision.USE_DEDICATED_SERVER) {
            return config.dedicatedServerBaseUrl();
        }

        if (config.autoStartEnabled() && process == null) {
            ProcessBuilder builder = new ProcessBuilder(config.sidecarStartCommand());
            builder.directory(config.sidecarWorkingDirectory().toFile());
            builder.redirectErrorStream(true);
            process = builder.start();
        }

        if (config.modKnowledgeScanEnabled()) {
            lastKnowledgeIndexes = modKnowledgeScanner.scan(config);
        }

        boolean localHealthy = isHealthy(config.localSidecarBaseUrl(), Duration.ofSeconds(2));
        if (localHealthy) {
            return config.localSidecarBaseUrl();
        }

        if (config.backendMode() == BackendMode.LOCAL) {
            throw runtimeUnavailable(config);
        }

        return config.dedicatedServerBaseUrl();
    }

    public synchronized List<SubsystemKnowledgeIndex> lastKnowledgeIndexes() {
        return List.copyOf(lastKnowledgeIndexes);
    }

    public boolean isHealthy(String baseUrl, Duration timeout) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newBuilder().build();
        HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl).resolve("/health"))
                .timeout(timeout == null ? Duration.ofSeconds(2) : timeout)
                .GET()
                .build();

        try {
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            return response.statusCode() < 400;
        } catch (IOException ioException) {
            return false;
        }
    }

    public synchronized void stop() {
        if (process != null) {
            process.destroy();
            process = null;
        }
    }

    private static AetherRuntimeUnavailableException runtimeUnavailable(HostingConfig config) {
        StringBuilder message = new StringBuilder();
        message.append("Local A.E.T.H.E.R runtime is required but unavailable at ")
                .append(config.localSidecarBaseUrl())
                .append(". Install/start the companion runtime (includes Ollama), then retry.");

        if (!config.runtimeInstallHelpUrl().isBlank()) {
            message.append(" Setup guide: ").append(config.runtimeInstallHelpUrl());
        }

        return new AetherRuntimeUnavailableException(message.toString());
    }
}
