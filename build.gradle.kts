plugins {
    base
}

group = "io.github.aether-core"
version = "0.1.0"

allprojects {
    group = rootProject.group
    version = rootProject.version

    repositories {
        mavenCentral()
    }
}
