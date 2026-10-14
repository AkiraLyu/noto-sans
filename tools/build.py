#!/usr/bin/env python3
"""Build the Noto Sans Akira desktop font family with fontTools."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import unicodedata

from fontTools import subset
from fontTools.pens.recordingPen import DecomposingRecordingPen, lerpRecordings
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTCollection, TTFont


FAMILY = "Noto Sans Akira"
VERSION = "1.000"
STYLES = {
    "Thin": 100,
    "Light": 300,
    "DemiLight": 350,
    "Regular": 400,
    "Medium": 500,
    "Bold": 700,
    "Black": 900,
}
RANGES = (
    (0x0020, 0x02FF),
    (0x0300, 0x052F),
    (0x1D00, 0x1FFF),
    (0x2000, 0x206F),
    (0x20A0, 0x20CF),
    (0x2100, 0x214F),
    (0x2C60, 0x2C7F),
    (0xA640, 0xA69F),
    (0xA720, 0xA7FF),
    (0xAB30, 0xAB6F),
    (0x1DF00, 0x1DFFF),
)
FEATURES = ("ccmp", "calt", "clig", "liga", "dlig", "kern", "mark", "mkmk")


def in_scope(codepoint: int) -> bool:
    return any(start <= codepoint <= end for start, end in RANGES)


def western_symbol(codepoint: int) -> bool:
    category = unicodedata.category(chr(codepoint))
    return category[0] in "PS" or category == "Zs"


def find_sc_face(path: Path) -> tuple[TTCollection, TTFont]:
    collection = TTCollection(path, lazy=True)
    for font in collection.fonts:
        if font["name"].getBestFamilyName() == "Noto Sans CJK SC":
            return collection, font
    collection.close()
    raise ValueError(f"No Noto Sans CJK SC face in {path}")


def substitutions(font: TTFont, tag: str) -> dict[str, set[str]]:
    layout = font["GSUB"].table
    indexes = {
        index
        for record in layout.FeatureList.FeatureRecord
        if record.FeatureTag == tag
        for index in record.Feature.LookupListIndex
    }
    result: dict[str, set[str]] = {}
    for index in sorted(indexes):
        lookup = layout.LookupList.Lookup[index]
        for table in lookup.SubTable:
            if lookup.LookupType == 7:
                table = table.ExtSubTable
            for source, target in getattr(table, "mapping", {}).items():
                result.setdefault(source, set()).add(target)
    return result


class SymbolSource:
    def __init__(self, directory: Path, style: str):
        first = "Light" if style == "DemiLight" else style
        self.font = TTFont(directory / f"NotoSans-{first}.ttf")
        self.cmap = self.font.getBestCmap()
        self.glyphs = self.font.getGlyphSet()
        self.second = (
            TTFont(directory / "NotoSans-Regular.ttf")
            if style == "DemiLight"
            else None
        )
        self.second_cmap = self.second.getBestCmap() if self.second else {}
        self.second_glyphs = self.second.getGlyphSet() if self.second else None

    def glyph(self, codepoint: int):
        name = self.cmap[codepoint]
        recording = DecomposingRecordingPen(self.glyphs)
        self.glyphs[name].draw(recording)
        width, bearing = self.font["hmtx"].metrics[name]
        if self.second and codepoint in self.second_cmap:
            other = self.second_cmap[codepoint]
            alternate = DecomposingRecordingPen(self.second_glyphs)
            self.second_glyphs[other].draw(alternate)
            try:
                value = list(lerpRecordings(recording.value, alternate.value, 0.5))
            except ValueError:
                # Some currency glyphs have different contour structures.
                # Retain the lighter source rather than alter their outlines.
                pass
            else:
                recording.value = value
                other_width, other_bearing = self.second["hmtx"].metrics[other]
                width = round((width + other_width) / 2)
                bearing = round((bearing + other_bearing) / 2)
        return recording, width, bearing

    def close(self):
        self.font.close()
        if self.second:
            self.second.close()


def rename(font: TTFont, style: str):
    postscript = f"NotoSansAkira-{style}"
    copyright_text = (
        "Original CJK outlines: © 2014-2021 Adobe (http://www.adobe.com/). "
        "Additional symbol outlines: Copyright 2022 The Noto Project Authors "
        "(https://github.com/notofonts/latin-greek-cyrillic)."
    )
    values = {
        0: copyright_text,
        1: FAMILY,
        2: style,
        3: f"{VERSION};AKRA;{postscript}",
        4: f"{FAMILY} {style}",
        5: f"Version {VERSION}",
        6: postscript,
        10: (
            "Western font derived from Noto Sans CJK SC. Original letter outlines "
            "and weights are retained. Western punctuation uses proportional "
            "forms; selected symbols and spaces come from Noto Sans."
        ),
        13: (
            "This Font Software is licensed under the SIL Open Font License, "
            "Version 1.1. See https://openfontlicense.org/"
        ),
        14: "https://openfontlicense.org/",
        16: FAMILY,
        17: style,
        21: FAMILY,
        22: style,
    }
    names = font["name"]
    names.names = [record for record in names.names if record.nameID not in values]
    for name_id, value in values.items():
        names.setName(value, name_id, 3, 1, 0x409)
        if value.isascii():
            names.setName(value, name_id, 1, 0, 0)
    top = font["CFF "].cff.topDictIndex[0]
    font["CFF "].cff.fontNames = [postscript]
    top.FamilyName = FAMILY
    top.FullName = f"{FAMILY} {style}"
    top.version = VERSION
    top.Notice = copyright_text.replace("©", "Copyright")
    font["head"].fontRevision = float(VERSION)
    font["head"].macStyle = 1 if style == "Bold" else 0
    font["OS/2"].usWeightClass = STYLES[style]
    font["OS/2"].fsSelection &= ~(1 | 32 | 64)
    font["OS/2"].fsSelection |= 32 if style == "Bold" else 64


def add_symbols(font: TTFont, donor: SymbolSource, points: set[int]):
    top = font["CFF "].cff.topDictIndex[0]
    glyph_order = list(font.getGlyphOrder())
    latin_gid = glyph_order.index(font.getBestCmap()[ord("A")])
    fd_index = top.FDSelect.gidArray[latin_gid]
    private = top.FDArray[fd_index].Private
    used_cids = {int(name[3:]) for name in glyph_order if name.startswith("cid")}
    free_cids = (value for value in range(1, 65535) if value not in used_cids)
    cmaps = [table.cmap for table in font["cmap"].tables if table.isUnicode()]
    source_names: dict[str, str] = {}
    for codepoint in sorted(points):
        source_name = donor.cmap[codepoint]
        if source_name not in source_names:
            recording, width, bearing = donor.glyph(codepoint)
            name = f"cid{next(free_cids):05d}"
            encoded_width = width - getattr(private, "nominalWidthX", 0)
            pen = T2CharStringPen(encoded_width, None, roundTolerance=0)
            recording.replay(pen)
            charstring = pen.getCharString(
                private=private, globalSubrs=font["CFF "].cff.GlobalSubrs
            )
            index = top.CharStrings.charStringsIndex
            top.CharStrings.charStrings[name] = len(index)
            index.append(charstring)
            top.FDSelect.gidArray.append(fd_index)
            glyph_order.append(name)
            top.charset.append(name)
            font["hmtx"].metrics[name] = (width, bearing)
            source_names[source_name] = name
        for cmap in cmaps:
            cmap[codepoint] = source_names[source_name]
    font.setGlyphOrder(glyph_order)
    font["maxp"].numGlyphs = len(glyph_order)


def build_style(cjk_directory: Path, latin_directory: Path, output: Path, style: str):
    source_path = cjk_directory / f"NotoSansCJK-{style}.ttc"
    collection, font = find_sc_face(source_path)
    donor = SymbolSource(latin_directory, style)
    try:
        assert font["head"].unitsPerEm == donor.font["head"].unitsPerEm == 1000
        original = dict(font.getBestCmap())
        metrics = font["hmtx"].metrics
        proportional = substitutions(font, "pwid")
        localized = substitutions(font, "locl")
        selected: dict[int, str] = {}
        imports: set[int] = set()
        for codepoint in sorted(set(original) | set(donor.cmap)):
            if not in_scope(codepoint):
                continue
            character = chr(codepoint)
            category = unicodedata.category(character)
            if category[0] == "C" or category in ("Zl", "Zp"):
                continue
            glyph = original.get(codepoint)
            if not glyph:
                if western_symbol(codepoint):
                    imports.add(codepoint)
                continue
            if codepoint >= 0x2000 and category == "Zs" and codepoint in donor.cmap:
                imports.add(codepoint)
                continue
            if codepoint > 0x7E and western_symbol(codepoint) and metrics[glyph][0] >= 1000:
                candidates = proportional.get(glyph, set()) | localized.get(glyph, set())
                narrower = [name for name in candidates if 0 < metrics[name][0] < metrics[glyph][0]]
                if narrower:
                    glyph = min(narrower, key=lambda name: (metrics[name][0], name))
                elif codepoint in donor.cmap:
                    imports.add(codepoint)
                    continue
                else:
                    # Characters without a proportional source use fallback.
                    continue
            selected[codepoint] = glyph
        for table in font["cmap"].tables:
            if table.isUnicode() and table.format != 14:
                table.cmap = {codepoint: glyph for codepoint, glyph in selected.items() if codepoint <= (0xFFFF if table.format == 4 else 0x10FFFF)}
        font["cmap"].tables = [table for table in font["cmap"].tables if table.isUnicode() and table.format != 14]
        options = subset.Options()
        options.layout_features = list(FEATURES)
        options.layout_scripts = ["DFLT", "latn", "grek", "cyrl"]
        options.name_IDs = ["*"]
        options.notdef_outline = True
        options.recalc_bounds = True
        worker = subset.Subsetter(options=options)
        worker.populate(unicodes=set(selected))
        worker.subset(font)
        for tag in ("BASE", "vhea", "vmtx", "VORG"):
            if tag in font:
                del font[tag]
        add_symbols(font, donor, imports)
        rename(font, style)
        cmap = font.getBestCmap()
        font["OS/2"].usFirstCharIndex = min(cmap)
        font["OS/2"].usLastCharIndex = min(max(cmap), 0xFFFF)
        font["OS/2"].recalcUnicodeRanges(font)
        font["OS/2"].recalcCodePageRanges(font)
        destination_directory = output.parent / "optional" if style == "DemiLight" else output
        destination_directory.mkdir(parents=True, exist_ok=True)
        destination = destination_directory / f"NotoSansAkira-{style}.otf"
        font.save(destination)
        print(f"{destination.name}: {len(cmap)} characters, {len(font.getGlyphOrder())} glyphs, {destination.stat().st_size} bytes")
    finally:
        donor.close()
        collection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cjk-dir", type=Path, default=Path("/usr/share/fonts/noto-cjk"))
    parser.add_argument("--latin-dir", type=Path, default=Path("/usr/share/fonts/noto"))
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1], help="Package directory containing fonts/ and optional/.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    for style in STYLES:
        build_style(args.cjk_dir, args.latin_dir, args.output / "fonts", style)


if __name__ == "__main__":
    main()
