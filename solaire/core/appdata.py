"""
Environment management for preferences and various application values.
ALl assuming Windows environment variables names and values.
"""


import json
import os
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Optional
from typing import Union


JSON_TYPE = Union[dict, list, int, float, bool, str, None]

_APPDATA_ROAMING_PATH = Path(os.environ['APPDATA'])
SOLAIRE_APPDATA_PATH = Path(_APPDATA_ROAMING_PATH, 'Solaire')
SOLAIRE_PREFERENCES_PATH = Path(SOLAIRE_APPDATA_PATH, 'preferences.json')


def export_data_to_json(path: Path, data: dict, overwrite: bool = False) -> None:
    """
    Export dict to json file path.

    Args:
        path (Path): the file path to place the .json file.
        data (dict): the data to export into the .json file.
        overwrite (bool): to overwrite json file if it already exists in path.
            Defaults to False.
    """
    if not path.exists() or overwrite:
        with open(path, 'w') as outfile:
            json.dump(data, outfile, indent=4)
    else:
        return


def import_data_from_json(filepath: Path) -> Optional[dict]:
    """
    Import data from a .json file.

    Args:
        filepath (Path): the filepath to the json file to extract data from.
    Returns:
        Optional[dict]: will return data if json file exists, else None.
    """
    if os.path.exists(filepath):
        with open(filepath) as file:
            data = json.load(file)
            return data

    return None


# -----Code Editor-------------------------------------------------------------

TAB_TYPE_SPACE = 'space'
TAB_TYPE_TAB = 'tab'


@dataclass
class CodePreferences(object):
    """Stylistic code values."""
    tab_type: str = TAB_TYPE_SPACE
    tab_space_width: int = 4
    enable_vertical_guide: bool = True
    guide_column: int = 80


@dataclass
class PythonCodeColor(object):
    """Syntax highlighting colors for Python."""
    keyword: list[int] = field(default_factory=lambda: [0, 255, 255])
    operator: list[int] = field(default_factory=lambda: [255, 255, 255])
    brace: list[int] = field(default_factory=lambda: [255, 0, 165])
    string_single: list[int] = field(default_factory=lambda: [144, 144, 238])
    string_triple: list[int] = field(default_factory=lambda: [0, 0, 100])
    comment: list[int] = field(default_factory=lambda: [255, 255, 0])
    numbers: list[int] = field(default_factory=lambda: [255, 255, 0])
    def_: list[int] = field(default_factory=lambda: [144, 144, 238])
    class_: list[int] = field(default_factory=lambda: [144, 144, 238])
    self_: list[int] = field(default_factory=lambda: [255, 0, 165])


@dataclass
class JsonCodeColor(object):
    """Syntax highlighting colors for JSON."""
    numeric: list[int] = field(default_factory=lambda: [255, 0, 165])
    key: list[int] = field(default_factory=lambda: [255, 255, 255])
    value: list[int] = field(default_factory=lambda: [144, 144, 238])


@dataclass
class Refresh(object):
    """The refresh rate of timer based code parsers / analyzers."""
    cursor: int = 16
    code_fold: int = 300


# -----Primary Preferences-----------------------------------------------------

@dataclass
class Preferences(object):
    code_preferences: CodePreferences = CodePreferences()
    python_code_color: PythonCodeColor = PythonCodeColor()
    json_code_color: JsonCodeColor = JsonCodeColor()
    refresh: Refresh = Refresh()

    def to_dict(self) -> dict[JSON_TYPE, JSON_TYPE]:
        return {
            'code_preferences': self.code_preferences.__dict__,
            'python_code_color': self.python_code_color.__dict__,
            'json_code_color': self.json_code_color.__dict__,
            'refresh': self.refresh.__dict__,
        }

    def from_dict(self, data: dict[JSON_TYPE, JSON_TYPE]) -> None:
        self.code_preferences.__dict__ = data['code_preferences']
        self.python_code_color.__dict__ = data['python_code_color']
        self.json_code_color.__dict__ = data['json_code_color']
        self.refresh.__dict__ = data['refresh']


PREFERENCES = Preferences()


if SOLAIRE_PREFERENCES_PATH.exists():
    PREFERENCES.from_dict(import_data_from_json(SOLAIRE_PREFERENCES_PATH))
else:
    SOLAIRE_APPDATA_PATH.mkdir(parents=True, exist_ok=True)
    default_data = PREFERENCES.to_dict()
    export_data_to_json(SOLAIRE_PREFERENCES_PATH, default_data)
