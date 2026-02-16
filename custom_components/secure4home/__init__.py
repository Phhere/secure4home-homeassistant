"""Secure4Home Integration for Home Assistant."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import requests

from .api import Secure4HomeAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Secure4Home from a config entry."""
    username = entry.data["username"]
    password = entry.data["password"]

    api = Secure4HomeAPI(username, password)

    try:
        await api.login()
    except Exception as err:
        _LOGGER.error("Failed to login to Secure4Home: %s", err)
        raise ConfigEntryAuthFailed(err) from err
        return False

    async def async_update_data():
        """Fetch data from API."""
        for i in range(0,3):
            try:
                # Get panel mode (current alarm status)
                mode_data = await api.get_panel_mode()
                # Get panel status (system health)
                status_data = await api.get_panel_status()

                # Combine data for sensors
                return {
                    "mode": mode_data,
                    "status": status_data,
                }
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    await api.login()
            except Exception as err:
                exception_type = type(err)
                raise UpdateFailed(f"Error communicating with API: {exception_type} {err}")
        raise UpdateFailed(f"Exceeded retries for API Communication")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Secure4Home",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
