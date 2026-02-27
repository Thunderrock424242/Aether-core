package io.github.aethercore.sdk;

import static org.junit.jupiter.api.Assertions.assertNotNull;

import org.junit.jupiter.api.Test;

class AetherClientTest {
    @Test
    void createsClient() {
        AetherClient client = new AetherClient("http://127.0.0.1:8765");
        assertNotNull(client);
    }
}
