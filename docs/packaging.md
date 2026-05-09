# Packaging

The open-source release path is portable-first.

## Recommended

Build a portable Windows app:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package-exe.ps1
```

The output is written to:

```text
apps\desktop\dist-electron
```

The portable app does not bundle `.env` or an API key. Users configure their own OpenAI-compatible endpoint on first launch.

## Why Portable First

Portable releases are easier for open-source users to inspect, download, remove, and test. A full installer can be added later if the project needs auto-update, file associations, or a signed distribution flow.
