# SPDX-FileCopyrightText: 2024 Sebastian Andersson <sebastian@bittr.nu>
# SPDX-License-Identifier: GPL-3.0-or-later

""" NFC tag handling """

import time
import logging
from threading import Lock, Event

import ndef
from py122u import nfc
import time


SPOOL = "SPOOL"
FILAMENT = "FILAMENT"
NDEF_TEXT_TYPE = "urn:nfc:wkt:T"

logger = logging.getLogger(__name__)


# pylint: disable=R0902
class NfcHandler:
    """NFC Tag handling"""

    def __init__(self, nfc_device: str):
        self.status = ""
        self.nfc_device = nfc_device
        self.on_nfc_no_tag_present = None
        self.on_nfc_tag_present = None
        self.should_stop_event = Event()
        self.write_lock = Lock()
        self.write_event = Event()
        self.write_spool = None
        self.write_filament = None

    def set_no_tag_present_callback(self, on_nfc_no_tag_present):
        """Sets a callback that will be called when no tag is present"""
        self.on_nfc_no_tag_present = on_nfc_no_tag_present

    def set_tag_present_callback(self, on_nfc_tag_present):
        """Sets a callback that will be called when a tag has been read"""
        self.on_nfc_tag_present = on_nfc_tag_present

    def write_to_tag(self, spool: int, filament: int) -> bool:
        """Writes spool & filament info to tag. Returns true if worked."""

        self._set_write_info(spool, filament)

        if self.write_event.wait(timeout=30):
            return True

        self._set_write_info(None, None)

        return False

    def getData(self, reader, block):
        try:
            data = reader.read_binary_blocks(block, 4)
            if data is not None:
                hex_data = " ".join(f"{b:02X}" for b in data)
                return int(hex_data.replace(" ", ""), 16)
            else:
                return 0
        except Exception as e:
            return 0
        
    def run(self):
        """Run the NFC handler, won't return"""
        reader = nfc.Reader()
        while True:
            try:
                reader.connect()
                filament_id = self.getData(reader, 45)
                spool_id = self.getData(reader, 46)
                if self.on_nfc_tag_present:
                    self.on_nfc_tag_present(spool_id, filament_id)
                time.sleep(10)
            except Exception as e:
                if self.on_nfc_no_tag_present:
                    self.on_nfc_no_tag_present()
                time.sleep(0.2)

    def stop(self):
        """Call to stop the handler"""
        self.should_stop_event.set()

    def _write_to_nfc_tag(self, tag, spool: int, filament: int) -> bool:
        """Write given spool/filament ids to the tag"""
        try:
            if tag.ndef and tag.ndef.is_writeable:
                tag.ndef.records = [
                    ndef.TextRecord(f"{SPOOL}:{spool}\n{FILAMENT}:{filament}\n")
                ]
                return True
            self.status = "Tag is write protected"
        except Exception as ex:  # pylint: disable=W0718
            logger.exception(ex)
            self.status = "Got error while writing"
        return False

    def _set_write_info(self, spool, filament):
        if self.write_lock.acquire():  # pylint: disable=R1732
            self.write_spool = spool
            self.write_filament = filament
            self.write_event.clear()
            self.write_lock.release()

    def _check_for_write_to_tag(self, tag) -> bool:
        """Check if the tag should be written to and do it"""
        did_write = False
        if self.write_lock.acquire():  # pylint: disable=R1732
            if self.write_spool:
                if self._write_to_nfc_tag(tag, self.write_spool, self.write_filament):
                    self.write_event.set()
                    did_write = True
                self.write_spool = None
                self.write_filament = None
            self.write_lock.release()
        return did_write