"""A bounded YAML-subset reader for the pipeline's file contracts (pack manifests and
structured document frontmatter). Stdlib-only, deterministic. Supports nested maps by
indentation, quoted scalars, ints/bools/null, flow lists, block lists of scalars and of maps
(indented OR at the parent key's indent), one nested map inside a list item, and inline `# `
comments outside quotes. It does NOT support folded/literal block scalars, anchors, inline
maps, or tabs — the file contracts do not use them in parsed positions."""
import re

_INT = re.compile(r"-?\d+$")


def parse_frontmatter(md_text: str) -> dict:
    m = re.match(r"﻿?\s*---\n(.*?)\n---", md_text or "", re.DOTALL)
    return parse_yaml(m.group(1)) if m else {}


def parse_yaml(text: str) -> dict:
    value, _ = _parse_map(_tokenize(text or ""), 0, 0)
    return value


def _strip_comment(s):
    out, q = [], None
    for c in s:
        if q:
            out.append(c)
            if c == q:
                q = None
        elif c in "\"'":
            q = c
            out.append(c)
        elif c == "#":
            break
        else:
            out.append(c)
    return "".join(out).rstrip()


def _tokenize(text):
    toks = []
    for raw in text.lstrip("﻿").splitlines():
        line = _strip_comment(raw)
        if line.strip():
            toks.append((len(line) - len(line.lstrip(" ")), line.strip()))
    return toks


def _split_flow(inner):
    parts, buf, q, depth = [], [], None, 0
    for c in inner:
        if q:
            buf.append(c)
            if c == q:
                q = None
        elif c in "\"'":
            q = c
            buf.append(c)
        elif c == "[":
            depth += 1
            buf.append(c)
        elif c == "]":
            depth -= 1
            buf.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


def _scalar(v):
    v = v.strip()
    if not v:
        return ""
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v[0] == "[" and v[-1] == "]":
        inner = v[1:-1].strip()
        return [_scalar(x) for x in _split_flow(inner)] if inner else []
    low = v.lower()
    if low in ("null", "~"):
        return None
    if low in ("true", "false"):
        return low == "true"
    if _INT.match(v):
        return int(v)
    return v


def _parse_map(toks, i, indent):
    out = {}
    while i < len(toks):
        ind, line = toks[i]
        if ind < indent or line.startswith("- "):
            break
        if ind > indent or ":" not in line:
            i += 1
            continue
        key, rest = line.split(":", 1)
        key, rest = key.strip(), rest.strip()
        if rest == "":
            j = i + 1
            if j < len(toks) and toks[j][0] > indent:
                out[key], i = _parse_block(toks, j, toks[j][0])
            elif j < len(toks) and toks[j][0] == indent and toks[j][1].startswith("- "):
                out[key], i = _parse_list(toks, j, indent)          # F5: same-indent block list
            else:
                out[key] = ""
                i += 1
        else:
            out[key] = _scalar(rest)
            i += 1
    return out, i


def _parse_block(toks, i, indent):
    if i < len(toks) and toks[i][1].startswith("- "):
        return _parse_list(toks, i, indent)
    return _parse_map(toks, i, indent)


def _parse_list(toks, i, indent):
    out = []
    while i < len(toks):
        ind, line = toks[i]
        if ind != indent or not line.startswith("- "):
            break
        rest = line[2:].strip()
        base = indent + 2
        item_lines = [(base, rest)]
        i += 1
        while i < len(toks) and toks[i][0] >= base:
            item_lines.append(toks[i])
            i += 1
        if ":" in rest and rest[0] not in "[\"'":
            item, _ = _parse_map(item_lines, 0, base)
            out.append(item)
        else:
            out.append(_scalar(rest))
    return out, i
