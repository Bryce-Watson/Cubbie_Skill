#!/usr/bin/env python3
"""Pantry to Plate: the student's food profile, saved word for word in one file.

The profile (allergies, diet, budget, kitchen, location and the rest) lives in
~/.config/pantry-to-plate/profile.json. It belongs to this student only, survives restarts and
Skill updates, and nothing in it changes unless one of these commands changes it:

    python3 scripts/food_profile.py show
    python3 scripts/food_profile.py add --allergy 'peanuts:severe' --diet 'vegetarian'
    python3 scripts/food_profile.py set --budget '$5 a meal' --location '78705' --kitchen 'microwave'
    python3 scripts/food_profile.py set --no-allergies
    python3 scripts/food_profile.py remove --dislike 'mushrooms'
    python3 scripts/food_profile.py remove --allergy 'peanuts' --confirmed
    python3 scripts/food_profile.py forget --field 'location'
    python3 scripts/food_profile.py forget --all --confirmed
    python3 scripts/food_profile.py --sample show     # the bundled sample profile; saves nothing

Anything that removes or loosens an allergy, or deletes the profile, is refused without
--confirmed, which Cubbie adds only after the student says yes.

Every command prints one JSON object. Exit codes: 0 done, 2 a command or value was rejected,
3 needs the student's yes (--confirmed), 4 not in the profile, 5 the saved profile can't be
read, 6 the profile couldn't be saved. Python 3.8+, standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SKILL_NAME = "pantry-to-plate"
SAMPLE_FILE = Path(__file__).resolve().parent.parent / "assets" / "sample_profile.json"
MAX_RECIPES = 30  # liked and disliked recipes kept, newest last

# command-line flag -> (key in the profile file, label used in confirmations)
LIST_FIELDS = {
    "diet": ("diet", "diet"),
    "dislike": ("dislikes", "dislikes"),
    "favorite": ("favorites", "favorites"),
    "kitchen": ("kitchen", "kitchen"),
    "staple": ("staples", "staples"),
    "store-like": ("stores_like", "stores you like"),
    "store-avoid": ("stores_avoid", "stores to avoid"),
    "loyalty-card": ("loyalty_cards", "loyalty cards"),
    "liked": ("liked_recipes", "liked recipes"),
    "disliked": ("disliked_recipes", "disliked recipes"),
}
SCALAR_FIELDS = {
    "budget": ("budget", "budget"),
    "location": ("location", "location"),
    "travel": ("travel", "travel"),
    "cook-time": ("cook_time", "cooking time"),
    "servings": ("servings", "servings"),
}
LABELS = {key: label for key, label in list(LIST_FIELDS.values()) + list(SCALAR_FIELDS.values())}
LOWERCASE = {"diet", "dislikes", "favorites", "kitchen", "staples"}  # store and recipe names keep their case
RECIPE_LISTS = {"liked_recipes": "disliked_recipes", "disliked_recipes": "liked_recipes"}
SEVERITIES = ("severe", "avoid", "unknown")  # unknown counts as severe until the student says otherwise
OFFERS = ("weekly-checkin", "google-tasks")
ANSWERS = ("accepted", "declined")
ESSENTIAL = ("allergies", "budget", "kitchen", "location")  # what `missing` reports, in the order to ask
FORGET = {"allergies": "allergies", "offers": "offers"}
FORGET.update({flag: key for flag, (key, _) in list(LIST_FIELDS.items()) + list(SCALAR_FIELDS.items())})
FORGET.update({key: key for key in LABELS})
STREET_ADDRESS = re.compile(
    r"^\s*\d+[a-z]?\s+(?:\S+\s+)*?(?:st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|way|ct|court|"
    r"pl|place|pkwy|parkway|hwy|highway|cir|circle|ter|terrace)\b\.?",
    re.IGNORECASE,
)
NEEDS_YES = ("Needs the student's yes first: {what}. Ask them in one line, then run the same command "
             "with --confirmed only if they say yes.")
UNREADABLE = ("The saved food profile can't be read. Don't suggest recipes yet: ask the student to confirm "
              "their allergies and diet again, run forget --all --confirmed, then save their answers fresh.")


class Stop(Exception):
    """Ends a command with a message for Cubbie and the exit code SKILL.md maps to a reply."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------- the file

def profile_path() -> Path:
    return Path.home() / ".config" / SKILL_NAME / "profile.json"


def empty_profile() -> dict:
    profile = {"version": 1, "allergies": None}  # None: never asked; []: the student said none
    profile.update({key: [] for key, _ in LIST_FIELDS.values()})
    profile.update({key: None for key, _ in SCALAR_FIELDS.values()})
    profile.update({"offers": {}, "updated_at": None})
    return profile


def checked(data: object) -> dict:
    """The saved data on top of an empty profile; Stop(5) if any part has the wrong shape."""
    if not isinstance(data, dict):
        raise Stop(5, UNREADABLE)
    profile = empty_profile()
    profile.update(data)
    allergies = profile["allergies"]
    ok = allergies is None or (isinstance(allergies, list) and all(
        isinstance(a, dict) and isinstance(a.get("item"), str) and a.get("severity") in SEVERITIES
        for a in allergies))
    ok = ok and all(isinstance(profile[key], list) and all(isinstance(v, str) for v in profile[key])
                    for key, _ in LIST_FIELDS.values())
    ok = ok and all(profile[key] is None or isinstance(profile[key], str) for key, _ in SCALAR_FIELDS.values())
    ok = ok and isinstance(profile["offers"], dict)
    if not ok:
        raise Stop(5, UNREADABLE)
    return profile


def load(sample: bool) -> tuple:
    """(profile, whether a saved profile exists). The sample is read from the Skill's own assets."""
    path = SAMPLE_FILE if sample else profile_path()
    if not path.exists():
        if sample:
            raise Stop(5, f"The bundled sample is missing: {SAMPLE_FILE}")
        return empty_profile(), False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Stop(5, UNREADABLE) from None
    return checked(data), True


def save(profile: dict) -> None:
    """Write the whole profile at once (a temporary file renamed over the old one), readable only by the student."""
    path = profile_path()
    profile["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tmp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".profile-", suffix=".tmp")  # mode 600
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
        tmp = None
    except OSError as exc:
        raise Stop(6, f"The profile couldn't be saved ({exc.strerror or exc}); it is unchanged. "
                      "Tell the student the change wasn't saved.") from None
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------- text

def clean(value: str) -> str:
    return " ".join(str(value).split())


def same(a: str, b: str) -> bool:
    return clean(a).casefold() == clean(b).casefold()


def attr(flag: str) -> str:
    return flag.replace("-", "_")


def normalized(key: str, raw: str) -> str:
    return clean(raw).lower() if key in LOWERCASE else clean(raw)


def allergy_label(allergy: dict) -> str:
    return allergy["item"] + (" (severe)" if allergy["severity"] == "severe" else "")


def allergies_on_file(profile: dict) -> str:
    if profile["allergies"] is None:
        return "not asked yet"
    return ", ".join(allergy_label(a) for a in profile["allergies"]) or "none"


def safety_line(profile: dict):
    """The line every recipe reply starts with, built only from the file; None until allergies are known."""
    if profile["allergies"] is None:
        return None
    parts = ["no " + allergy_label(a) for a in profile["allergies"]] or ["no allergies"]
    return "Checked against your profile: " + ", ".join(parts + profile["diet"]) + "."


def missing(profile: dict) -> list:
    gaps = ["allergies"] if profile["allergies"] is None else []
    return gaps + [key for key in ESSENTIAL[1:] if not profile[key]]


def parse_allergy(raw: str) -> tuple:
    item, _, severity = raw.partition(":")
    item, severity = clean(item).lower(), clean(severity).lower() or "unknown"
    if not item:
        raise Stop(2, "Name the allergy, like --allergy 'peanuts:severe'.")
    if severity not in SEVERITIES:
        raise Stop(2, f"An allergy's severity is severe or avoid (or leave it out), not {severity!r}.")
    return item, severity


# ---------------------------------------------------------------- commands

def cmd_add(args, profile: dict, changes: list) -> None:
    for raw in args.allergy or []:
        item, severity = parse_allergy(raw)
        allergies = profile["allergies"] if profile["allergies"] is not None else []
        found = next((a for a in allergies if a["item"] == item), None)
        if found is None:
            allergies.append({"item": item, "severity": severity})
            changes.append(f"Added allergy: {item}" + (f" ({severity})" if severity != "unknown" else ""))
        elif severity != "unknown" and severity != found["severity"]:
            if found["severity"] == "severe" and not args.confirmed:
                raise Stop(3, NEEDS_YES.format(what=f"changing {item} from severe to avoid"))
            found["severity"] = severity
            changes.append(f"Updated allergy: {item} ({severity})")
        profile["allergies"] = allergies
    for flag, (key, label) in LIST_FIELDS.items():
        for raw in getattr(args, attr(flag)) or []:
            value = normalized(key, raw)
            if not value or any(same(value, v) for v in profile[key]):
                continue
            profile[key].append(value)
            changes.append(f"Added to {label}: {value}")
            if key in RECIPE_LISTS:  # a recipe is liked or disliked, not both
                other = RECIPE_LISTS[key]
                profile[other] = [v for v in profile[other] if not same(v, value)]
                del profile[key][:-MAX_RECIPES]


def cmd_set(args, profile: dict, changes: list) -> None:
    for flag, (key, label) in SCALAR_FIELDS.items():
        raw = getattr(args, attr(flag))
        if raw is None:
            continue
        value = clean(raw)
        if not value:
            raise Stop(2, f"--{flag} needs a value; to clear it, use forget --field {flag}.")
        if key == "location" and STREET_ADDRESS.match(value):
            raise Stop(2, "That looks like a street address. Save a ZIP code or campus name instead.")
        if key == "budget" and not re.search(r"\d", value):  # "$5 a meal" in double quotes arrives as " a meal"
            raise Stop(2, "The budget needs an amount, like '$5 a meal'. Use single quotes: a dollar sign "
                          "inside double quotes disappears.")
        if profile[key] != value:
            profile[key] = value
            changes.append(f"Set {label}: {value}")
    for flag, (key, label) in LIST_FIELDS.items():
        raws = getattr(args, attr(flag))
        if raws is None:
            continue
        values = []
        for raw in raws:
            value = normalized(key, raw)
            if value and not any(same(value, v) for v in values):
                values.append(value)
        if values != profile[key]:
            profile[key] = values
            changes.append(f"Set {label}: {', '.join(values) or 'none'}")
    if args.no_allergies and profile["allergies"] != []:
        if profile["allergies"] and not args.confirmed:
            raise Stop(3, NEEDS_YES.format(what=f"clearing the allergies on file ({allergies_on_file(profile)})"))
        removed = f" (removed {allergies_on_file(profile)})" if profile["allergies"] else ""
        profile["allergies"] = []
        changes.append("Saved: no allergies" + removed)
    for raw in args.offer or []:
        name, _, answer = raw.partition("=")
        name, answer = clean(name).lower(), clean(answer).lower()
        if name not in OFFERS or answer not in ANSWERS:
            raise Stop(2, "Use --offer 'NAME=ANSWER', with NAME weekly-checkin or google-tasks "
                          "and ANSWER accepted or declined.")
        if profile["offers"].get(name) != answer:
            profile["offers"][name] = answer
            changes.append(f"Saved: {name} {answer}")


def cmd_remove(args, profile: dict, changes: list) -> None:
    for raw in args.allergy or []:
        item = parse_allergy(raw)[0]
        allergies = profile["allergies"] or []
        found = next((a for a in allergies if a["item"] == item), None)
        if found is None:
            raise Stop(4, f"{item} isn't in the allergies on file ({allergies_on_file(profile)}). "
                          "Ask the student what they meant.")
        if not args.confirmed:
            raise Stop(3, NEEDS_YES.format(what=f"removing {item} from the allergies"))
        allergies.remove(found)
        changes.append(f"Removed allergy: {item}")
    for flag, (key, label) in LIST_FIELDS.items():
        for raw in getattr(args, attr(flag)) or []:
            found = next((v for v in profile[key] if same(v, raw)), None)
            if found is None:
                on_file = ", ".join(profile[key]) or "nothing"
                raise Stop(4, f"{clean(raw)} isn't in {label} (on file: {on_file}). Ask the student what they meant.")
            profile[key].remove(found)
            changes.append(f"Removed from {label}: {found}")


def cmd_forget(args, profile: dict, changes: list) -> None:
    for raw in args.field:
        key = FORGET.get(clean(raw).lower())
        if key is None:
            names = ", ".join(["allergies", "offers"] + list(LIST_FIELDS) + list(SCALAR_FIELDS))
            raise Stop(2, f"Unknown field {clean(raw)!r}. Use one of: {names}.")
        if key == "allergies":
            if profile["allergies"] and not args.confirmed:
                raise Stop(3, NEEDS_YES.format(what=f"forgetting the allergies on file ({allergies_on_file(profile)})"))
            if profile["allergies"] is not None:
                profile["allergies"] = None
                changes.append("Forgot allergies (ask again before suggesting recipes)")
        elif key == "offers":
            if profile["offers"]:
                profile["offers"] = {}
                changes.append("Forgot the answers to follow-up offers")
        elif profile[key]:
            profile[key] = [] if isinstance(profile[key], list) else None
            changes.append(f"Forgot {LABELS[key]}")


def forget_all(args, sample: bool) -> dict:
    if not args.confirmed:
        raise Stop(3, NEEDS_YES.format(what="deleting the whole food profile, allergies included"))
    path = profile_path()
    existed = path.exists()
    if existed and not sample:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise Stop(6, f"The profile couldn't be deleted ({exc.strerror or exc}).") from None
    return {"ok": True, "changed": existed, "saved": existed and not sample,
            "confirmation": "Deleted your whole food profile, allergies included.",
            "safety_line": None, "missing": list(ESSENTIAL), "sample": sample}


def run(args) -> dict:
    sample = bool(getattr(args, "sample", False))
    if args.command == "forget" and args.all:
        return forget_all(args, sample)
    profile, exists = load(sample)
    if args.command == "show":
        return {"ok": True, "exists": exists, "safety_line": safety_line(profile), "missing": missing(profile),
                "sample": sample, "profile": profile}
    before = json.dumps(profile, sort_keys=True)
    changes: list = []
    {"add": cmd_add, "set": cmd_set, "remove": cmd_remove, "forget": cmd_forget}[args.command](args, profile, changes)
    changed = json.dumps(profile, sort_keys=True) != before
    if changed and not sample:
        save(profile)
    confirmation = (". ".join(changes) if changes else "Nothing changed") + f". Allergies on file: {allergies_on_file(profile)}."
    return {"ok": True, "changed": changed, "saved": changed and not sample, "confirmation": confirmation,
            "safety_line": safety_line(profile), "missing": missing(profile), "sample": sample}


# ---------------------------------------------------------------- command line

def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--sample", action="store_true", default=argparse.SUPPRESS,
                        help="use the bundled sample profile and save nothing")
    parser = argparse.ArgumentParser(prog="food_profile.py", description="The student's food profile for Pantry to Plate.")
    parser.add_argument("--sample", action="store_true", help="use the bundled sample profile and save nothing")
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    sub.add_parser("show", parents=[common], help="read the profile (changes nothing)")

    add = sub.add_parser("add", parents=[common], help="add to the profile")
    add.add_argument("--allergy", action="append", metavar="ITEM:SEVERITY")
    for flag in LIST_FIELDS:
        add.add_argument(f"--{flag}", action="append", metavar="VALUE")
    add.add_argument("--confirmed", action="store_true", help="the student said yes (needed to lower an allergy from severe)")

    set_ = sub.add_parser("set", parents=[common], help="set single values, or replace a whole list")
    for flag in SCALAR_FIELDS:
        set_.add_argument(f"--{flag}", metavar="VALUE")
    for flag in LIST_FIELDS:
        set_.add_argument(f"--{flag}", action="append", metavar="VALUE")
    set_.add_argument("--no-allergies", action="store_true", help="the student said they have no allergies")
    set_.add_argument("--offer", action="append", metavar="NAME=ANSWER",
                      help="weekly-checkin or google-tasks, accepted or declined")
    set_.add_argument("--confirmed", action="store_true", help="the student said yes (needed to clear listed allergies)")

    remove = sub.add_parser("remove", parents=[common], help="remove items")
    remove.add_argument("--allergy", action="append", metavar="ITEM")
    for flag in LIST_FIELDS:
        remove.add_argument(f"--{flag}", action="append", metavar="VALUE")
    remove.add_argument("--confirmed", action="store_true", help="the student said yes (needed to remove an allergy)")

    forget = sub.add_parser("forget", parents=[common], help="clear a field, or delete the whole profile")
    which = forget.add_mutually_exclusive_group(required=True)
    which.add_argument("--field", action="append", metavar="FIELD")
    which.add_argument("--all", action="store_true")
    forget.add_argument("--confirmed", action="store_true", help="the student said yes (needed for allergies or --all)")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except Stop as stop:
        print(json.dumps({"ok": False, "code": stop.code, "error": str(stop)}, ensure_ascii=False))
        return stop.code
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
