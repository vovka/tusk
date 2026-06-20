# Drop a static (musl) codex binary here as `codex` to bake it into the image.
# Build it from your Codex source:
#   cargo build --release --target x86_64-unknown-linux-musl
#   cp target/x86_64-unknown-linux-musl/release/codex vendor/codex
# The binary itself is gitignored (large, machine-specific).
