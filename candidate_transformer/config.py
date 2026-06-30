"""
Module: candidate_transformer.config

Loads, validates, and holds system configurations, default settings,
and field selections.
"""

import json
from typing import Any, Dict, Optional


class Config:
    """
    Container class for system configuration parameters.
    """

    def __init__(self, config_path: str = "") -> None:
        """
        Initialize the system configuration, optionally from a JSON file.
        """
        # Documented default configuration
        self.config_data = {
            "include_confidence": True,
            "include_provenance": True,
            "on_missing": "null",
            "fields": None,
        }

        if config_path:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate configuration shape
            if not isinstance(data, dict):
                raise ValueError("Config must be a JSON object")

            # Validate include_confidence
            if "include_confidence" in data:
                if not isinstance(data["include_confidence"], bool):
                    raise ValueError("include_confidence must be a boolean")
                self.config_data["include_confidence"] = data["include_confidence"]

            # Validate include_provenance
            if "include_provenance" in data:
                if not isinstance(data["include_provenance"], bool):
                    raise ValueError("include_provenance must be a boolean")
                self.config_data["include_provenance"] = data["include_provenance"]

            # Validate on_missing
            if "on_missing" in data:
                if data["on_missing"] not in ("null", "omit", "error"):
                    raise ValueError("on_missing must be one of 'null', 'omit', 'error'")
                self.config_data["on_missing"] = data["on_missing"]

            # Validate fields
            if "fields" in data:
                fields = data["fields"]
                if fields is not None:
                    if not isinstance(fields, list):
                        raise ValueError("fields must be a list of objects")
                    validated_fields = []
                    for idx, f_cfg in enumerate(fields):
                        if not isinstance(f_cfg, dict):
                            raise ValueError(f"fields[{idx}] must be an object")
                        if "from" not in f_cfg:
                            raise ValueError(
                                f"fields[{idx}] is missing required property 'from'"
                            )
                        if not isinstance(f_cfg["from"], str):
                            raise ValueError(
                                f"fields[{idx}] property 'from' must be a string"
                            )

                        validated_item = {"from": f_cfg["from"]}
                        if "to" in f_cfg:
                            if not isinstance(f_cfg["to"], str):
                                raise ValueError(
                                    f"fields[{idx}] property 'to' must be a string"
                                )
                            validated_item["to"] = f_cfg["to"]
                        validated_fields.append(validated_item)
                    self.config_data["fields"] = validated_fields

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration parameter.
        """
        return self.config_data.get(key, default)
