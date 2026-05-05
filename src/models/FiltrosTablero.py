from dataclasses import dataclass

@dataclass
class FiltroTablero:
    zona: list[str]|None = None
    aps: list[str]|None = None
    mes: list[str]|None = None
    sector: list[str]|None = None

