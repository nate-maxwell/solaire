"""
Environment management for preferences and various application values.
All assuming Windows environment variables names and values.
"""


import json
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Optional
from typing import Union

from solaire.core import broker


JSON_TYPE = Union[dict, list, int, float, bool, str, None]

_APPDATA_PATH = Path.home() / 'AppData'
_APPDATA_ROAMING_PATH = _APPDATA_PATH / 'Roaming'

SOLAIRE_APPDATA_PATH = Path(_APPDATA_ROAMING_PATH, 'Solaire')
SOLAIRE_APPDATA_PATH.mkdir(parents=True, exist_ok=True)

SOLAIRE_PREFERENCES_PATH = Path(SOLAIRE_APPDATA_PATH, 'Preferences.json')
SOLAIRE_SESSION_DATA_PATH = Path(SOLAIRE_APPDATA_PATH, 'SessionData.json')


broker.register_source('SYSTEM')


class AppdataError(Exception):
    """Errors for unhandled appdata values."""


def export_data_to_json(path: Path, data: dict, overwrite: bool = False) -> None:
    """
    Export dict to JSON file path.

    Args:
        path (Path): the file path to place the .json file.
        data (dict): the data to export into the .json file.
        overwrite (bool): to overwrite JSON file if it already exists in path.
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
        filepath (Path): the filepath to the JSON file to extract data from.
    Returns:
        Optional[dict]: will return data if JSON file exists, else None.
    """
    if filepath.exists():
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
    enable_auto_suggest: bool = True
    suggestion_depth: int = 32


@dataclass
class PythonCodeColor(object):
    """Syntax highlighting colors for Python."""
    keyword: str = '#00ffff'
    operator: str = '#ffffff'
    brace: str = '#ffa500'
    string_single: str = '#90ee90'
    string_triple: str = '#006400'
    comment: str = '#ff00ff'
    numbers: str = '#ff00ff'
    def_: str = '#00ffff'
    class_: str = '#00ffff'
    self_: str = '#ffa500'


@dataclass
class JsonCodeColor(object):
    """Syntax highlighting colors for JSON."""
    numeric: str = '#ffa500'
    key: str = '#ffffff'
    value: str = '#90ee90'


@dataclass
class Refresh(object):
    """The refresh rate of timer based code parsers / analyzers."""
    cursor: int = 16
    code_fold: int = 600


@dataclass
class Theme(object):
    """Theme and color management."""
    theme_file: str = 'COMBINEAR'


# -----Primary Preferences-----------------------------------------------------

class Preferences(object):
    """
    Singleton container holding all preferences data for the application.

    Checks roaming appdata for preferences file. If the file is found, class
    populates itself from file contents. Otherwise, file is created using class
    defaults.
    """

    _instance: Optional['Preferences'] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> 'Preferences':
        if cls._instance is None:
            cls._instance = super(Preferences, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Prevent re-initialization on subsequent calls
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        # Defaults
        self.code_preferences: CodePreferences = CodePreferences()
        self.python_code_color: PythonCodeColor = PythonCodeColor()
        self.json_code_color: JsonCodeColor = JsonCodeColor()
        self.refresh: Refresh = Refresh()
        self.theme: Theme = Theme()

        # First-time load from disk (if present), else create defaults
        if SOLAIRE_PREFERENCES_PATH.exists():
            self.load()
        else:
            self.save()

    def to_dict(self) -> dict[str, JSON_TYPE]:
        """Serialize to a plain dict."""
        return {
            'code_preferences': asdict(self.code_preferences),
            'python_code_color': asdict(self.python_code_color),
            'json_code_color': asdict(self.json_code_color),
            'refresh': asdict(self.refresh),
            'theme': asdict(self.theme)
        }

    def from_dict(self, data: dict[str, JSON_TYPE]) -> None:
        """Apply a serialized dict into dataclass fields safely."""
        if 'code_preferences' in data:
            self.code_preferences = CodePreferences(**data['code_preferences'])
        if 'python_code_color' in data:
            self.python_code_color = PythonCodeColor(**data['python_code_color'])
        if 'json_code_color' in data:
            self.json_code_color = JsonCodeColor(**data['json_code_color'])
        if 'refresh' in data:
            self.refresh = Refresh(**data['refresh'])
        if 'theme' in data:
            self.theme = Theme(**data['theme'])

    def load(self) -> None:
        """
        Load in data from user appdata file if it can be found, otherwise, save
        default data to user appdata folder.
        """
        data = import_data_from_json(SOLAIRE_PREFERENCES_PATH)
        if data is not None:
            self.from_dict(data)

    def save(self) -> None:
        """
        Save current data to user's appdata folder.
        Emit event signaling a potential update to preference data.
        Emitted data is None as the preference singleton can be accessed from
        anywhere.
        """
        export_data_to_json(SOLAIRE_PREFERENCES_PATH, self.to_dict(), True)
        event = broker.Event('SYSTEM', 'PREFERENCES_UPDATED')
        broker.emit(event)


# -----Session Data------------------------------------------------------------


class SessionData(object):
    """
    Singleton container holding all session specific values.
    Values such as the current opened directory, or other things necessary for
    the client to function.
    """

    _instance: Optional['SessionData'] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> 'SessionData':
        if cls._instance is None:
            cls._instance = super(SessionData, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Prevent re-initialization on subsequent calls
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        # -----Data-----
        self.project_directory = Path(Path.cwd().anchor)

        # First-time load from disk (if present), else create defaults
        if SOLAIRE_SESSION_DATA_PATH.exists():
            self.load()
        else:
            self.save()

    def to_dict(self) -> dict[str, JSON_TYPE]:
        """Serialize to a plain dict."""
        return {
            'project_directory': self.project_directory.as_posix()
        }

    def from_dict(self, data: dict[str, JSON_TYPE]) -> None:
        """Apply a serialized dict into dataclass fields safely."""
        self.project_directory = Path(data.get('project_directory', self.project_directory))

    def load(self) -> None:
        """
        Load in data from user appdata file if it can be found, otherwise, save
        default data to user appdata folder.
        """
        data = import_data_from_json(SOLAIRE_SESSION_DATA_PATH)
        if data is not None:
            self.from_dict(data)

    def save(self) -> None:
        """
        Save current data to user's appdata folder.
        Emit event signaling a potential update to preference data.
        Emitted data is None as the preference singleton can be accessed from
        anywhere.
        """
        export_data_to_json(SOLAIRE_SESSION_DATA_PATH, self.to_dict(), True)
        event = broker.Event('SYSTEM', 'SESSION_DATA_UPDATED')
        broker.emit(event)


def initialize() -> None:
    """Call on startup to ensure the preferences singleton is loaded."""
    _ = Preferences()  # Ensures singleton is populated by constructor.
    _ = SessionData()
