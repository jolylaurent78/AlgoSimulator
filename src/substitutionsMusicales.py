"""Substitutions musicales communes aux cadrans, sans dépendance aux algorithmes."""
from src.calculAstronomique import decalageGamme


def _noteSourceClef2(notes):
    """Première note définie pour Clef 2 : initiale, puis +2, puis -2."""
    return next((note for note in (notes[0], notes[2], notes[1]) if note in ("C", "F")), None)


def noteAvecSubstitution(note, substitution):
    """Conserver les choix historiques ; Clef 2 envoie Do ou Fa vers Sol."""
    notes = decalageGamme(note)
    if substitution == "Clef 2":
        # Sol et les autres cas sans correspondance définie gardent leur note.
        return "G" if _noteSourceClef2(notes) is not None else note
    return notes[{"=": 0, "+2": 2, "-2": 1, "Clef": 3}[substitution]]
