import html
import re
from collections import defaultdict


def _extract_cham_tokens(raw_values):
    tokens = []
    for raw in raw_values:
        if raw is None:
            continue

        text = str(raw).strip()
        if not text:
            continue

        bracket_tokens = re.findall(r"\(([A-Za-z0-9_]+-[A-Za-z0-9_]+)\)", text)
        if bracket_tokens:
            tokens.extend(bracket_tokens)
            continue

        for part in [x.strip() for x in text.split(",") if str(x).strip()]:
            tokens.append(part)

    return tokens


def _compact_cham_tokens(tokens):
    grouped = defaultdict(list)
    passthrough = []

    for token in tokens:
        s = str(token or "").strip().upper()
        if not s:
            continue

        m = re.match(r"^([A-Z0-9_]+)-([A-Z0-9_]+)$", s)
        if not m:
            passthrough.append(s)
            continue

        body = m.group(1)
        cham = m.group(2)
        if cham not in grouped[body]:
            grouped[body].append(cham)

    result = []
    for body in sorted(grouped.keys()):
        suffixes = grouped[body]
        if len(suffixes) == 1:
            result.append(f"{body}-{suffixes[0]}")
        else:
            result.append(f"{body}-" + ";".join(suffixes))

    for p in passthrough:
        if p not in result:
            result.append(p)

    return ", ".join(result)


def _parse_eqpgroup_tokens(eqpgroup_text):
    if not eqpgroup_text:
        return []

    raw = str(eqpgroup_text).strip().upper()
    if raw == "":
        return []

    normalized = raw.replace("(", "").replace(")", "")
    normalized = normalized.replace(",", "_").replace(";", "_").replace(":", "_")
    parts = [x.strip() for x in normalized.split("_") if str(x).strip()]

    tokens = []
    for part in parts:
        s = str(part or "").strip().upper()
        if not s:
            continue
        if "-" in s:
            s = s.split("-", 1)[0].strip()
        if s and s not in tokens:
            tokens.append(s)
    return tokens


def _flatten_body_values(values):
    tokens = []
    for raw in values:
        for token in _parse_eqpgroup_tokens(raw):
            if token and token not in tokens:
                tokens.append(token)
    return tokens


def _parse_path_members(path_text, eqpgroup_text):
    members = []
    cham_tokens = [str(x).strip().upper() for x in _extract_cham_tokens([path_text]) if str(x).strip()]
    seen = set()

    if cham_tokens:
        for tok in cham_tokens:
            m = re.match(r"^([A-Z0-9_]+)-([A-Z0-9_]+)$", tok)
            if m:
                body = m.group(1)
                cham = m.group(2)
                key = f"{body}-{cham}"
                if key in seen:
                    continue
                seen.add(key)
                members.append({
                    "eqp_body_name": body,
                    "eqp_cham_name": cham,
                    "member_key": key,
                    "display_name": key,
                    "has_cham": True,
                })
            else:
                key = tok
                if key in seen:
                    continue
                seen.add(key)
                members.append({
                    "eqp_body_name": tok,
                    "eqp_cham_name": "",
                    "member_key": tok,
                    "display_name": tok,
                    "has_cham": False,
                })
        return members

    eqps = _parse_eqpgroup_tokens(eqpgroup_text)
    for body in eqps:
        if body in seen:
            continue
        seen.add(body)
        members.append({
            "eqp_body_name": body,
            "eqp_cham_name": "",
            "member_key": body,
            "display_name": body,
            "has_cham": False,
        })

    return members


def _normalize_path_text(path_text):
    raw = str(path_text or "").strip().upper()
    if not raw:
        return ""
    members = _parse_path_members(raw, "")
    parts = []
    for m in members:
        body = str(m.get("eqp_body_name") or "").strip().upper()
        cham = str(m.get("eqp_cham_name") or "").strip().upper()
        token = f"{body}-{cham}" if body and cham else body
        if token and token not in parts:
            parts.append(token)
    return ", ".join(parts)


def _parse_childeqp_groups(childeqp_text):
    text = str(childeqp_text or "").strip().upper()
    if not text:
        return []
    groups = []
    for group_text in [g.strip() for g in text.split(';') if g.strip()]:
        members = []
        for member in [m.strip() for m in group_text.split(':') if m.strip()]:
            body = member.split('-', 1)[0].strip()
            if body and body not in members:
                members.append(body)
        if members:
            groups.append(tuple(members))
    return groups


def _path_signature(row):
    path_text = _normalize_path_text(getattr(row, "path", "") or "")
    if path_text:
        return path_text
    groups = _parse_childeqp_groups(getattr(row, "childeqp", "") or "")
    if groups:
        return tuple(groups)
    path_members = _parse_path_members(getattr(row, "path", ""), getattr(row, "eqpgroup", ""))
    bodies = []
    for m in path_members:
        body = str(m.get("eqp_body_name") or "").strip().upper()
        if body and body not in bodies:
            bodies.append(body)
    return ", ".join(bodies)


def _merge_eqpgroup_html(source_eqps, manual_eqps):
    parts = []
    seen = set()

    def _norm(v):
        s = str(v or "").strip().upper().replace("(", "").replace(")", "")
        if "-" in s:
            s = s.split("-", 1)[0].strip()
        return s

    for s in source_eqps:
        norm = _norm(s)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        parts.append(html.escape(norm))

    for s in manual_eqps:
        norm = _norm(s)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        parts.append(f'<span class="manual-added-text">{html.escape(norm)}</span>')

    return ", ".join(parts) if parts else "-"


def _merge_cham_html(source_chams, manual_chams):
    source_compact = _compact_cham_tokens(source_chams)
    manual_compact = _compact_cham_tokens(manual_chams)

    parts = []
    if source_compact:
        parts.append(html.escape(source_compact))
    if manual_compact:
        parts.append(f'<span class="manual-added-text">{html.escape(manual_compact)}</span>')

    return ", ".join(parts) if parts else "-"
