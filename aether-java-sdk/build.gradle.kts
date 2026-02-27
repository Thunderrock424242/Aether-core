plugins {
    `java-library`
    `maven-publish`
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
    withSourcesJar()
    withJavadocJar()
}

dependencies {
    testImplementation(platform("org.junit:junit-bom:5.11.3"))
    testImplementation("org.junit.jupiter:junit-jupiter")
}

tasks.test {
    useJUnitPlatform()
}

publishing {
    publications {
        create<MavenPublication>("gpr") {
            from(components["java"])
            artifactId = "aether-java-sdk"
            pom {
                name.set("Aether Java SDK")
                description.set("Java client for integrating Minecraft NeoForge mods with the A.E.T.H.E.R AI sidecar.")
                url.set("https://github.com/${System.getenv("GITHUB_REPOSITORY") ?: "OWNER/REPO"}")
            }
        }
    }

    repositories {
        maven {
            name = "GitHubPackages"
            url = uri("https://maven.pkg.github.com/${System.getenv("GITHUB_REPOSITORY") ?: "OWNER/REPO"}")
            credentials {
                username = System.getenv("GITHUB_ACTOR") ?: providers.gradleProperty("gpr.user").orNull
                password = System.getenv("GITHUB_TOKEN") ?: providers.gradleProperty("gpr.key").orNull
            }
        }
    }
}
