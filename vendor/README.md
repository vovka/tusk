# Codex binary for the codex_exec agent backend

Drop a **static (musl)** codex binary here as `codex` to bake it into the image.
A glibc-linked build will NOT run (the bookworm base ships glibc 2.36). When
absent, the image still builds and only the default `tusk` backend is available.

The binary is gitignored (large, machine-specific).

## Easiest source: the published musl release via npm

```sh
cd /tmp && npm pack @openai/codex@<version>-linux-x64
tar -xzf openai-codex-*-linux-x64.tgz
cp package/vendor/x86_64-unknown-linux-musl/bin/codex \
   /path/to/repo/vendor/codex
```

Use a version new enough for your account's models. With a ChatGPT (OAuth)
login, older releases fail with "model is not supported when using Codex with a
ChatGPT account" / "requires a newer version of Codex". 0.141.0 works with
gpt-5.5; pin `CODEX_EXEC_MODEL` in `.env` to a model your release+account allow.

## Or build from source

```sh
cargo build --release --target x86_64-unknown-linux-musl
cp target/x86_64-unknown-linux-musl/release/codex vendor/codex
```
