# Local Dashboard Telemetry

[![Tests](https://github.com/Scottimus/Local-Dashboard-Telemetry/actions/workflows/tests.yml/badge.svg)](https://github.com/Scottimus/Local-Dashboard-Telemetry/actions/workflows/tests.yml)

A localhost service with GPU/system snapshots and a small browser panel. GPU field normalization and cache behavior are adapted from an existing PowerShell dashboard backend into a focused Python service.

```sh
python telemetry.py --sample
```

Open `http://127.0.0.1:8766`. Sample mode uses fictional responses and needs only Python's standard library. Both API responses identify whether they are sample data and whether they came from the two-second cache.

For live system data, install `requirements.txt` and run without `--sample`. NVIDIA GPU data additionally requires `nvidia-smi` on PATH. The first GPU is displayed. A missing, failed, or timed-out sensor returns HTTP 503 with `sensor_unavailable`. The service binds only to localhost and exposes no account integrations.

```sh
python -m unittest discover -s tests -v
```
