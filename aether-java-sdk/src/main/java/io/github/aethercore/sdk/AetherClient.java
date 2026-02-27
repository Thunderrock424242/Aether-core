package io.github.aethercore.sdk;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Objects;

/**
 * Lightweight Java client for calling A.E.T.H.E.R sidecar endpoints from JVM mods.
 */
public final class AetherClient {
    private final HttpClient httpClient;
    private final URI baseUri;
    private final Duration timeout;
    private final String bearerToken;

    public AetherClient(String baseUrl) {
        this(baseUrl, null, Duration.ofSeconds(30));
    }

    public AetherClient(String baseUrl, String bearerToken, Duration timeout) {
        this.httpClient = HttpClient.newBuilder().build();
        this.baseUri = URI.create(Objects.requireNonNull(baseUrl, "baseUrl"));
        this.timeout = timeout == null ? Duration.ofSeconds(30) : timeout;
        this.bearerToken = bearerToken;
    }

    public String generate(String sessionId, String prompt, String subsystem) throws IOException, InterruptedException {
        Objects.requireNonNull(sessionId, "sessionId");
        Objects.requireNonNull(prompt, "prompt");
        String payload = "{" +
                "\"session_id\":\"" + escapeJson(sessionId) + "\"," +
                "\"prompt\":\"" + escapeJson(prompt) + "\"," +
                "\"subsystem\":\"" + escapeJson(subsystem == null ? "Sentinel" : subsystem) + "\"" +
                "}";

        HttpRequest.Builder builder = HttpRequest.newBuilder(baseUri.resolve("/generate"))
                .header("Content-Type", "application/json")
                .timeout(timeout)
                .POST(HttpRequest.BodyPublishers.ofString(payload, StandardCharsets.UTF_8));

        if (bearerToken != null && !bearerToken.isBlank()) {
            builder.header("Authorization", "Bearer " + bearerToken);
        }

        HttpResponse<String> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        if (response.statusCode() >= 400) {
            throw new IOException("Aether /generate failed: HTTP " + response.statusCode() + " body=" + response.body());
        }
        return response.body();
    }

    public String warmup(String subsystem) throws IOException, InterruptedException {
        Objects.requireNonNull(subsystem, "subsystem");
        URI warmupUri = baseUri.resolve("/backend/warmup?subsystem=" + subsystem);
        HttpRequest.Builder builder = HttpRequest.newBuilder(warmupUri)
                .timeout(timeout)
                .POST(HttpRequest.BodyPublishers.noBody());

        if (bearerToken != null && !bearerToken.isBlank()) {
            builder.header("Authorization", "Bearer " + bearerToken);
        }

        HttpResponse<String> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        if (response.statusCode() >= 400) {
            throw new IOException("Aether /backend/warmup failed: HTTP " + response.statusCode() + " body=" + response.body());
        }
        return response.body();
    }

    private static String escapeJson(String value) {
        return value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r");
    }
}
