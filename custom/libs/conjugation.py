"""Tableau de conjugaison d'un verbe japonais, calculé à partir de son écriture, de
sa lecture et de son groupe (`partofspeech.uid`). Rien n'est stocké en base.

`conjugate()` renvoie une ligne par forme (présent, passé, forme en て...), chacune
déclinée en registre neutre/poli et affirmatif/négatif. Une case vaut `None` quand la
combinaison n'a pas d'usage courant. Chaque case donne `writing` (kanji) et `reading`
(kana), obtenus en conjuguant séparément l'écriture et la lecture du verbe.

`conjugate()` renvoie `None` si le mot n'est pas un verbe ou si sa terminaison ne
correspond pas à son groupe (on préfère ne rien afficher qu'une forme fausse).
"""

from dataclasses import dataclass
from functools import partial
from typing import Callable

# Terminaison du dictionnaire -> (rangées a, i, e, o de la consonne, suffixe en て).
_GODAN_ROWS = {
    "う": ("わ", "い", "え", "お", "って"),
    "く": ("か", "き", "け", "こ", "いて"),
    "ぐ": ("が", "ぎ", "げ", "ご", "いで"),
    "す": ("さ", "し", "せ", "そ", "して"),
    "つ": ("た", "ち", "て", "と", "って"),
    "ぬ": ("な", "に", "ね", "の", "んで"),
    "ぶ": ("ば", "び", "べ", "ぼ", "んで"),
    "む": ("ま", "み", "め", "も", "んで"),
    "る": ("ら", "り", "れ", "ろ", "って"),
}

# Verbes honorifiques en -る : base en い (ください, なさいます) au lieu de り.
_HONORIFIC_READINGS = ("なさる", "くださる", "いらっしゃる", "おっしゃる", "ござる")

# 行く se conjugue en って (行って) et non en いて ; 〜ていく en est l'auxiliaire.
_IKU_WRITING_SUFFIXES = ("行く", "ていく", "でいく")
_IKU_WRITINGS = ("いく", "ゆく")

_LABELS = {
    "present": "Présent",
    "past": "Passé",
    "te": "Forme en て",
    "volitional": "Volitif",
    "imperative": "Impératif",
    "conditional_ba": "Conditionnel en ば",
    "conditional_tara": "Conditionnel en たら",
    "potential": "Potentiel",
    "passive": "Passif",
    "causative": "Causatif",
    "causative_passive": "Causatif-passif",
}

# ある n'a pas d'usage courant à ces formes (le potentiel se dit あり得る).
_ARU_MISSING_FORMS = {
    "volitional",
    "imperative",
    "potential",
    "passive",
    "causative",
    "causative_passive",
}


@dataclass(frozen=True)
class _Stems:
    """Formes de base d'un verbe, dont se déduit tout le tableau (voir `_forms`).
    `potential`, `passive`, `causative` et `causative_passive` sont des verbes en る
    à part entière, conjugués comme des ichidan."""

    dictionary: str
    negative: str  # devant ない
    continuative: str  # devant ます
    te: str
    volitional: str
    imperative: str
    conditional: str
    potential: str
    passive: str
    causative: str
    causative_passive: str


def _godan(text: str, *, iku: bool = False, aru: bool = False, honorific: bool = False) -> _Stems:
    base = text[:-1]
    a, i, e, o, te = _GODAN_ROWS[text[-1]]
    if iku:
        te = "って"
    if honorific:
        i = "い"
    return _Stems(
        dictionary=text,
        # ある n'a pas de base négative : sa négation est ない tout court.
        negative="" if aru else base + a,
        continuative=base + i,
        te=base + te,
        volitional=f"{base}{o}う",
        imperative=base + (i if honorific else e),
        conditional=f"{base}{e}ば",
        potential=f"{base}{e}る",
        passive=f"{base}{a}れる",
        causative=f"{base}{a}せる",
        causative_passive=f"{base}{a}せられる",
    )


def _ichidan(text: str) -> _Stems:
    base = text[:-1]
    return _Stems(
        dictionary=text,
        negative=base,
        continuative=base,
        te=f"{base}て",
        volitional=f"{base}よう",
        imperative=f"{base}ろ",
        conditional=f"{base}れば",
        potential=f"{base}られる",
        passive=f"{base}られる",
        causative=f"{base}させる",
        causative_passive=f"{base}させられる",
    )


def _suru(text: str) -> _Stems:
    """する et ses composés (勉強する)."""
    base = text[:-2]
    return _Stems(
        dictionary=text,
        negative=f"{base}し",
        continuative=f"{base}し",
        te=f"{base}して",
        volitional=f"{base}しよう",
        imperative=f"{base}しろ",
        conditional=f"{base}すれば",
        potential=f"{base}できる",
        passive=f"{base}される",
        causative=f"{base}させる",
        causative_passive=f"{base}させられる",
    )


def _kuru(text: str) -> _Stems:
    """来る et ses composés (持ってくる). La voyelle du radical change en kana (こ, き,
    く) mais pas en kanji, où elle reste 来."""
    base = text[:-2]
    ko, ki, ku = ("来", "来", "来") if text.endswith("来る") else ("こ", "き", "く")
    return _Stems(
        dictionary=text,
        negative=base + ko,
        continuative=base + ki,
        te=f"{base}{ki}て",
        volitional=f"{base}{ko}よう",
        imperative=f"{base}{ko}い",
        conditional=f"{base}{ku}れば",
        potential=f"{base}{ko}られる",
        passive=f"{base}{ko}られる",
        causative=f"{base}{ko}させる",
        causative_passive=f"{base}{ko}させられる",
    )


def _stems_builder(writing: str, reading: str, pos_uid: str | None) -> Callable[[str], _Stems] | None:
    """Fonction à appliquer à l'écriture et à la lecture, `None` si le mot n'est pas
    un verbe ou si sa terminaison ne correspond pas à son groupe."""
    if writing[-1] != reading[-1]:
        return None
    if pos_uid == "verb_ichidan":
        return _ichidan if reading[-1] == "る" else None
    if pos_uid == "verb_godan":
        if reading[-1] not in _GODAN_ROWS:
            return None
        return partial(
            _godan,
            iku=writing in _IKU_WRITINGS or writing.endswith(_IKU_WRITING_SUFFIXES),
            aru=reading == "ある",
            honorific=reading.endswith(_HONORIFIC_READINGS),
        )
    if pos_uid == "verb_irregular":
        if reading.endswith("する") and writing.endswith("する"):
            return _suru
        if reading.endswith("くる") and writing.endswith(("来る", "くる")):
            return _kuru
    return None


def _ichidan_forms(verb: str) -> tuple[str, str, str, str]:
    base = verb[:-1]
    return verb, f"{base}ない", f"{base}ます", f"{base}ません"


def _forms(stems: _Stems) -> dict[str, tuple[str | None, str | None, str | None, str | None]]:
    """Par forme : (neutre affirmatif, neutre négatif, poli affirmatif, poli négatif)."""
    negative, continuative, te = stems.negative, stems.continuative, stems.te
    past = te[:-1] + ("だ" if te[-1] == "で" else "た")
    return {
        "present": (stems.dictionary, f"{negative}ない", f"{continuative}ます", f"{continuative}ません"),
        "past": (past, f"{negative}なかった", f"{continuative}ました", f"{continuative}ませんでした"),
        "te": (te, f"{negative}ないで", None, None),
        "volitional": (stems.volitional, None, f"{continuative}ましょう", None),
        "imperative": (stems.imperative, f"{stems.dictionary}な", f"{te}ください", f"{negative}ないでください"),
        "conditional_ba": (stems.conditional, f"{negative}なければ", None, None),
        "conditional_tara": (f"{past}ら", f"{negative}なかったら", None, None),
        "potential": _ichidan_forms(stems.potential),
        "passive": _ichidan_forms(stems.passive),
        "causative": _ichidan_forms(stems.causative),
        "causative_passive": _ichidan_forms(stems.causative_passive),
    }


def _cell(writing: str | None, reading: str | None) -> dict | None:
    return None if writing is None else {"writing": writing, "reading": reading}


def conjugate(writing: str | None, reading: str | None, pos_uid: str | None) -> list[dict] | None:
    if not writing or not reading:
        return None
    build = _stems_builder(writing, reading, pos_uid)
    if build is None:
        return None

    written, read = _forms(build(writing)), _forms(build(reading))
    missing = _ARU_MISSING_FORMS if reading == "ある" else set()
    rows = []
    for uid, label in _LABELS.items():
        if uid in missing:
            continue
        plain, plain_negative, polite, polite_negative = (
            _cell(w, r) for w, r in zip(written[uid], read[uid])
        )
        rows.append(
            {
                "uid": uid,
                "label": label,
                "plain": {"affirmative": plain, "negative": plain_negative},
                "polite": {"affirmative": polite, "negative": polite_negative},
            }
        )
    return rows
