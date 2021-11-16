# Mi Temperature and Humidity Sensor 2 sensor for HomeAssistant

This is an integration for Mi Temperature and Humidity Sensor 2 sensor


### Installation

Copy this folder to `<config_dir>/custom_components/mitemphumidity/`.

Add the following entry in your `configuration.yaml`:

```yaml
sensor:
  - platform: mitemphumidity
    mac: 00:00:00:00:00:00
    name: MiTempHumidity #optional
    adapter: hci0 #optional
    retries: 5 #optional
    timeout: 10 #optional
```