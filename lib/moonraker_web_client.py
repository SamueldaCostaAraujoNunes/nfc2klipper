# SPDX-FileCopyrightText: 2024 Sebastian Andersson <sebastian@bittr.nu>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Moonraker Web Client"""

import requests
import json


# pylint: disable=R0903
class MoonrakerWebClient:
    """Moonraker Web Client"""

    def __init__(self, url: str):
        self.url = url

    def set_spool_and_filament(self, spool: int, filament: int):
        """Calls moonraker with the current spool & filament"""

 
        url = "http://192.168.0.125:7125/printer/gcode/script"
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "script": f"MMU_GATE_MAP NEXT_SPOOLID={spool}"
        }

        response = requests.request("GET", url, headers=headers, data=json.dumps(payload))
        print(response)
        if response.status_code != 200:
            raise ValueError(f"Request to moonraker failed: {response}")
