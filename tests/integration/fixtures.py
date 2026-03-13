"""
Smart-home integration test dataset.

14 notes about home automation — rooms, devices, automations, infrastructure.
Chosen so that:
  - semantic search queries have clear expected results
  - keyword terms (MQTT, Zigbee, Frigate, …) appear in predictable notes
  - the link graph has 3 well-connected hubs and isolated leaves

Graph structure (directed, but graph-search is undirected):

  Morning Routine ──triggers──► Bedroom Lighting
  Morning Routine ──triggers──► Kitchen Appliances
  Morning Routine ──controls──► Thermostat Schedule
  Away Mode       ──triggers──► Motion Sensors
  Away Mode       ──triggers──► Security Cameras
  Away Mode       ──controls──► Thermostat Schedule
  Home Assistant  ──integrates_with──► MQTT Broker
  Home Assistant  ──integrates_with──► Security Cameras
  Home Assistant  ──integrates_with──► Voice Assistant
  Thermostat      ──monitors──► Energy Monitoring
  Garden Irrig.   ──triggers──► Motion Sensors
  Guest Mode      ──controls──► Living Room AV
  Guest Mode      ──controls──► Security Cameras
"""

# ── Note definitions ──────────────────────────────────────────────────────────

NOTES = [
    {
        "title": "Morning Routine Automation",
        "content": (
            "Automation triggered at 6:30am on weekdays. "
            "Gradually increases bedroom lights to 80% brightness over 15 minutes. "
            "Starts coffee maker in the kitchen via smart plug. "
            "Sets thermostat to 21°C for the day. "
            "Plays morning news playlist on Sonos speakers. "
            "Sends a wake-up notification to phone."
        ),
        "tags": ["automation", "schedule", "morning"],
    },
    {
        "title": "Bedroom Lighting Scene",
        "content": (
            "Warm white lights at 2700K dimmed to 20% for sleep mode. "
            "Activated automatically at 10pm or by voice command. "
            "Blackout blinds close automatically at sunset. "
            "Night light stays at 5% brightness for safe movement. "
            "Sunrise alarm gradually brightens lights from 5% to 60% over 30 minutes."
        ),
        "tags": ["lighting", "bedroom", "scene"],
    },
    {
        "title": "Living Room AV Setup",
        "content": (
            "Samsung 65-inch TV connected to Apple TV 4K and PS5. "
            "Sonos Arc soundbar with surround rear speakers. "
            "Philips Hue smart lights set to cinema scene when TV turns on via HDMI-CEC. "
            "Motorised blinds auto-close at sunset for movie viewing. "
            "Harmony hub controls all AV devices from single remote."
        ),
        "tags": ["living-room", "lighting", "entertainment"],
    },
    {
        "title": "Kitchen Appliances Integration",
        "content": (
            "Smart coffee maker scheduled via Home Assistant automation. "
            "Oven temperature sensor reports to HA dashboard. "
            "Fridge temperature monitored via Zigbee sensor — alert if above 8°C. "
            "Dishwasher energy consumption tracked via Shelly Plug S. "
            "Extractor fan activates automatically when kitchen humidity exceeds 70%."
        ),
        "tags": ["kitchen", "appliances", "sensors", "energy"],
    },
    {
        "title": "Away Mode Configuration",
        "content": (
            "Activates when all residents leave home, detected via phone GPS geofencing. "
            "Turns off all lights and non-essential appliances. "
            "Arms the security system and locks smart lock. "
            "Sets thermostat to eco mode at 17°C to save energy. "
            "Activates random lighting simulation to deter burglars. "
            "Sends notification when away mode is triggered."
        ),
        "tags": ["automation", "security", "away"],
    },
    {
        "title": "Motion Sensor Network",
        "content": (
            "PIR sensors installed in hallway (x2), front garden, back garden, and garage. "
            "All running Zigbee protocol via ConBee II coordinator on Raspberry Pi. "
            "Night-time: hallway motion triggers corridor lights at 30% brightness. "
            "Garden sensors trigger outdoor floodlight and start security camera recording. "
            "Telegram bot sends alerts for motion detected after 11pm."
        ),
        "tags": ["sensors", "security", "zigbee"],
    },
    {
        "title": "Thermostat Schedule and Zones",
        "content": (
            "Heating zones: ground floor, first floor, master bedroom. "
            "Weekday schedule: 6am–9am at 21°C, 5pm–11pm at 21°C, otherwise 17°C. "
            "Weekend schedule: 8am–11pm at 21°C. "
            "Weather compensation: reduces target by 0.5°C per degree above 10°C outside. "
            "Each zone has independent Netatmo smart valve and temperature sensor. "
            "Integrates with energy monitoring to track heating cost per zone."
        ),
        "tags": ["heating", "schedule", "zones", "energy"],
    },
    {
        "title": "Home Assistant Core Configuration",
        "content": (
            "Home Assistant OS running on Raspberry Pi 4 with 4GB RAM. "
            "Static IP: 192.168.1.10. Supervised installation for add-on support. "
            "Key integrations: Zigbee2MQTT, MQTT broker, Philips Hue bridge, Sonos, Netatmo. "
            "SSL certificate via Let's Encrypt. Remote access through Nabu Casa cloud. "
            "Automations backed up nightly to NAS via samba share. "
            "Frigate NVR add-on installed for AI-based camera person detection."
        ),
        "tags": ["home-assistant", "setup", "infrastructure"],
    },
    {
        "title": "MQTT Broker Setup",
        "content": (
            "Mosquitto MQTT broker running as Home Assistant add-on. "
            "Local port 1883, SSL port 8883 for external clients. "
            "All Zigbee devices publish state changes via Zigbee2MQTT topics. "
            "Topic structure: zigbee2mqtt/device_name for devices, homeassistant/# for discovery. "
            "Retained messages enabled so HA recovers state after restart. "
            "Password authentication required; ACL limits per-device topic access."
        ),
        "tags": ["mqtt", "setup", "infrastructure", "zigbee"],
    },
    {
        "title": "Security Camera System",
        "content": (
            "Four Reolink RLC-810A cameras: front door, back garden, garage, side gate. "
            "All PoE powered and connected to 8-port PoE switch. "
            "Frigate NVR integration with Home Assistant for real-time person detection. "
            "Motion detection zones configured to reduce false positives from traffic. "
            "30-day local recording retention on 4TB HDD in NAS. "
            "Telegram alerts sent immediately when person detected on any camera."
        ),
        "tags": ["security", "cameras", "surveillance"],
    },
    {
        "title": "Voice Assistant Integration",
        "content": (
            "Google Home hub in kitchen and living room for voice control. "
            "Amazon Echo Dot in master bedroom as alarm and media controller. "
            "Both integrated with Home Assistant via Nabu Casa cloud connector. "
            "Custom routines defined: 'Good morning', 'Goodnight', 'Movie time', 'I am leaving'. "
            "Voice commands control all lights, thermostat, locks, and media playback. "
            "Guest access mode disables sensitive commands like disarming security."
        ),
        "tags": ["voice-assistant", "integration", "automation"],
    },
    {
        "title": "Energy Monitoring Dashboard",
        "content": (
            "Shelly EM clamp monitors on main consumer unit for whole-house power consumption. "
            "Individual appliance monitoring via Shelly Plug S on fridge, washing machine, EV charger. "
            "Solar panel output tracked via SolarEdge local API integration. "
            "Grafana dashboard shows real-time consumption and 90-day historical trends. "
            "Daily alert if consumption exceeds 20 kWh. "
            "Monthly export to CSV for energy cost analysis."
        ),
        "tags": ["energy", "monitoring", "solar", "dashboard"],
    },
    {
        "title": "Garden Irrigation System",
        "content": (
            "Orbit B-hyve controller with 6 irrigation zones: front lawn, back lawn, two flower beds, vegetable patch, greenhouse. "
            "Integrated with Home Assistant via B-hyve custom integration. "
            "Smart scheduling skips watering if rain forecast exceeds 4mm in next 24 hours. "
            "Soil moisture sensors in vegetable patch prevent overwatering. "
            "All zones run at 6am to minimise water evaporation. "
            "Motion sensors in garden pause irrigation if movement detected."
        ),
        "tags": ["garden", "irrigation", "automation", "sensors"],
    },
    {
        "title": "Guest Mode Automation",
        "content": (
            "Temporary guest WiFi SSID activates with randomised password for stay duration. "
            "Guest bedroom lights set to warm welcoming scene at 60% brightness. "
            "Bathroom underfloor heating set to 22°C two hours before guest arrival. "
            "Smart lock generates a temporary PIN code valid only for the stay. "
            "Living room TV pre-configured with streaming apps visible. "
            "Security motion alerts suppressed in guest bedroom and bathroom."
        ),
        "tags": ["automation", "guest", "lighting", "security"],
    },
]

# ── Link definitions (source_title, target_title, relation_type) ─────────────

LINKS = [
    # Morning Routine hub
    ("Morning Routine Automation",   "Bedroom Lighting Scene",       "triggers"),
    ("Morning Routine Automation",   "Kitchen Appliances Integration","triggers"),
    ("Morning Routine Automation",   "Thermostat Schedule and Zones", "controls"),
    # Away Mode hub
    ("Away Mode Configuration",      "Motion Sensor Network",         "triggers"),
    ("Away Mode Configuration",      "Security Camera System",        "triggers"),
    ("Away Mode Configuration",      "Thermostat Schedule and Zones", "controls"),
    # Home Assistant hub
    ("Home Assistant Core Configuration", "MQTT Broker Setup",        "integrates_with"),
    ("Home Assistant Core Configuration", "Security Camera System",   "integrates_with"),
    ("Home Assistant Core Configuration", "Voice Assistant Integration", "integrates_with"),
    # Thermostat → Energy
    ("Thermostat Schedule and Zones","Energy Monitoring Dashboard",   "monitors"),
    # Garden → Motion
    ("Garden Irrigation System",     "Motion Sensor Network",         "triggers"),
    # Guest Mode → AV + Cameras
    ("Guest Mode Automation",        "Living Room AV Setup",          "controls"),
    ("Guest Mode Automation",        "Security Camera System",        "controls"),
]

# ── Buffer note samples ───────────────────────────────────────────────────────

BUFFER_NOTES = [
    {"content": "Check if zigbee coordinator firmware needs updating", "meta": {"source": "manual"}},
    {"content": "Look into Matter protocol support for future device purchases", "meta": {"source": "research"}},
    {"content": "Investigate Home Assistant Energy dashboard for solar ROI calculation", "meta": None},
    {"content": "Consider adding water leak sensors under kitchen sink and washing machine", "meta": {"priority": "high"}},
    {"content": "Review camera retention policy — 30 days may exceed storage", "meta": {"source": "review"}},
]


# ── Seed function ─────────────────────────────────────────────────────────────

def seed_data(client) -> dict[str, str]:
    """
    Seed the integration DB via the API.

    Creates all 14 notes (embeddings generated inline since embedding_mode=sync),
    then creates all links between them.

    Returns a dict mapping note title → note UUID.
    """
    note_ids: dict[str, str] = {}

    # 1. Create notes
    for note in NOTES:
        resp = client.post("/api/notes/", json=note)
        assert resp.status_code == 201, f"Failed to create note '{note['title']}': {resp.text}"
        note_ids[note["title"]] = resp.json()["id"]

    # 2. Create links
    for source_title, target_title, relation_type in LINKS:
        resp = client.post("/api/notes/links", json={
            "source_id": note_ids[source_title],
            "target_id": note_ids[target_title],
            "relation_type": relation_type,
        })
        assert resp.status_code == 201, (
            f"Failed to create link {source_title!r} → {target_title!r}: {resp.text}"
        )

    return note_ids
