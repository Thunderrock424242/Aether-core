package io.github.aethercore.sdk;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;

class AetherClientTest {
    @Test
    void createsClient() {
        AetherClient client = new AetherClient("http://127.0.0.1:8765");
        assertNotNull(client);
    }

    @Test
    void generateUsesMessageFieldAndAutoSubsystemByDefault() throws IOException, InterruptedException {
        AtomicReference<String> requestBody = new AtomicReference<>();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/generate", exchange -> {
            requestBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            byte[] response = "ok".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        server.start();

        try {
            AetherClient client = new AetherClient("http://127.0.0.1:" + server.getAddress().getPort());
            String response = client.generate("session-1", "hello world", null);

            assertEquals("ok", response);
            assertEquals(
                    "{\"session_id\":\"session-1\",\"message\":\"hello world\",\"subsystem\":\"Auto\"}",
                    requestBody.get());
        } finally {
            server.stop(0);
        }
    }
}
