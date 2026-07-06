# pico-sensor-logger
pico-sensor-logger repo

## Project structure

```text
main.py             Application entry point
config.json         Runtime configuration
config_loader.py    Configuration loading and validation
devices/            Access point and SCD40 hardware modules
core/               Shared sensor data, connector, and time service
storage/            File access and CSV writing
web/                TCP server, HTTP server, and chart rendering
```
