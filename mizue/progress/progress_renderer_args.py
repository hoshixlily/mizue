from dataclasses import dataclass
from abc import ABC
from typing import Optional


@dataclass
class BaseRendererArgs(ABC):
    percentage: float
    value: int


@dataclass
class InfoSeparatorRendererArgs(BaseRendererArgs):
    separator: Optional[str]
    pass


@dataclass
class InfoTextRendererArgs(BaseRendererArgs):
    text: str


@dataclass
class LabelRendererArgs(BaseRendererArgs):
    label: Optional[str]


@dataclass
class PercentageRendererArgs(BaseRendererArgs):
    pass


@dataclass
class ProgressBarRendererArgs(BaseRendererArgs):
    text: str
    width: int


@dataclass
class SpinnerRendererArgs(BaseRendererArgs):
    spinner: str
