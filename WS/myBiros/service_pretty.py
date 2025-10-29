# service_pretty.py
# -*- coding: utf-8 -*-
"""
Pretty printer per payload di estrazione documentale + liste di output.
Nessuna dipendenza esterna (solo standard library).
"""

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Tuple, Union, DefaultDict
from collections import defaultdict
from datetime import datetime
import csv
import io
import sys

__all__ = [
    # payload -> tabelle
    "pretty_service_response",
    "rows_from_payload",
    "to_markdown",
    "to_csv",
    # output list -> tabelle
    "pretty_output",
    "to_markdown_output",
    "to_csv_output",
]

Entity = Union[Dict[str, Any], str, float, int]


# ---------------------- UTIL COMUNI ----------------------

def _as_list(v: Any) -> List[Entity]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def _best_entity(entities: List[Entity]) -> Tuple[str, Union[float, None]]:
    best_text, best_conf = "", None
    for e in entities:
        if isinstance(e, dict):
            text = str(e.get("text", "")).strip()
            conf = e.get("confidence", None)
        else:
            text = str(e).strip()
            conf = None
        if not text:
            continue
        if best_conf is None or (isinstance(conf, (int, float)) and conf > best_conf):
            best_text, best_conf = text, conf
    return best_text, best_conf


def _fmt_conf(conf: Any) -> str:
    if conf is None or conf == "":
        return ""
    try:
        s = f"{float(conf):.2f}".replace(",", ".")
        return s.rstrip("0").rstrip(".")
    except Exception:
        return str(conf)


def _print_table(headers: List[str], rows: List[List[str]], stream=None) -> None:
    if stream is None:
        stream = sys.stdout
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))
    def line(char: str = "-") -> str:
        return "+".join(char * (w + 2) for w in widths)
    def fmt_row(cols: Iterable[str]) -> str:
        return "|".join(f" {c:<{w}} " for c, w in zip(cols, widths))
    print(line("-"), file=stream)
    print(fmt_row(headers), file=stream)
    print(line("="), file=stream)
    for r in rows:
        print(fmt_row(r), file=stream)
        print(line("-"), file=stream)


# ---------------------- RACCOLTA ENTITÀ DAL PAYLOAD ----------------------

def _collect_entities_from_summary(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Raccoglie entità da document_summary.entities se disponibili."""
    entities = (((data.get("document_summary") or {}).get("entities")) or {})
    result: Dict[str, List[Dict[str, Any]]] = {}
    for k, v in entities.items():
        items = _as_list(v)
        # Normalizza: tieni solo dict con almeno 'text'
        norm = []
        for e in items:
            if isinstance(e, dict):
                t = str(e.get("text", "")).strip()
                if t:
                    norm.append({"text": t, "confidence": e.get("confidence", None)})
            else:
                t = str(e).strip()
                if t:
                    norm.append({"text": t, "confidence": None})
        if norm:
            result[k] = norm
    return result


def _collect_entities_from_pages(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Raccoglie entità da document_pages[*].entities e anche da
    document_pages[*].aggregated_entities (es. gruppi con tag_aggregation).
    """
    result: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    pages = _as_list(data.get("document_pages"))

    for page in pages:
        # 1) entità dirette
        ents = (page or {}).get("entities") or {}
        for k, v in ents.items():
            for e in _as_list(v):
                if isinstance(e, dict):
                    t = str(e.get("text", "")).strip()
                    if t:
                        result[k].append({"text": t, "confidence": e.get("confidence", None)})
                else:
                    t = str(e).strip()
                    if t:
                        result[k].append({"text": t, "confidence": None})

        # 2) aggregated_entities: ogni item ha "aggregated_fields": { field_key: {id,text,confidence} }
        aggs = (page or {}).get("aggregated_entities") or {}
        for _, items in aggs.items():
            for item in _as_list(items):
                fields = (item or {}).get("aggregated_fields") or {}
                for fld_key, fld_val in fields.items():
                    if isinstance(fld_val, dict):
                        t = str(fld_val.get("text", "")).strip()
                        if t:
                            result[fld_key].append({"text": t, "confidence": fld_val.get("confidence", None)})

    return result


def _merge_entities(primary: Dict[str, List[Dict[str, Any]]],
                    secondary: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """Unione semplice dei dizionari chiave -> lista di entità."""
    merged: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    keys = set(primary.keys()) | set(secondary.keys())
    for k in keys:
        merged[k].extend(primary.get(k, []))
        merged[k].extend(secondary.get(k, []))
    return merged


def _collect_all_entities(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Ritorna un dizionario { field_key: [ {text, confidence}, ... ] }.
    Preferisce document_summary.entities; se vuoto, integra con document_pages.
    Sempre integra eventuali aggregated_entities dalle pagine.
    """
    from_summary = _collect_entities_from_summary(data)
    from_pages = _collect_entities_from_pages(data)
    if from_summary:
        # integra comunque quanto trovato nelle pagine/aggregati (non sovrascrive)
        return _merge_entities(from_summary, from_pages)
    else:
        return from_pages


# ---------------------- PAYLOAD -> TABELLE ----------------------

def rows_from_payload(
    data: Dict[str, Any],
    prefer: str = "best",
    include_empty: bool = False,
) -> List[List[str]]:
    """
    Crea righe tabellari:
    [Alias, Chiave, Valore, Conf., Multi, Presente]
    - usa document_summary.entities se presente, altrimenti document_pages[*].entities
    - include anche aggregated_entities delle pagine
    """
    service_fields = data.get("service_fields", {}) or {}
    entities = _collect_all_entities(data)  # dict key -> list of dict{text,confidence}
    rows: List[List[str]] = []

    # unisci le chiavi presenti in service_fields e in entities
    all_keys = sorted(set(service_fields.keys()) | set(entities.keys()))

    for key in all_keys:
        field_meta = service_fields.get(key, {})
        alias = field_meta.get("tag_alias", key)
        multi = field_meta.get("tag_multiple_values", False)

        items = _as_list(entities.get(key, []))

        present = "No"
        value_str = ""
        conf_str = ""

        if prefer == "best":
            text, conf = _best_entity(items)
            if text:
                present = "Sì"
                value_str = text
                conf_str = _fmt_conf(conf)
        else:  # "all"
            texts: List[str] = []
            confs: List[str] = []
            for e in items:
                if isinstance(e, dict):
                    t = str(e.get("text", "")).strip()
                    c = _fmt_conf(e.get("confidence", None))
                else:
                    t = str(e).strip()
                    c = ""
                if t:
                    texts.append(t)
                    if c:
                        confs.append(c)
            if texts:
                present = "Sì"
            value_str = " | ".join(texts)
            conf_str = " | ".join(confs)

        row = [
            str(alias),
            str(key),
            value_str,
            conf_str,
            "Sì" if multi else "No",
            present,
        ]
        if include_empty or present == "Sì":
            rows.append(row)

    return rows


def pretty_service_response(
    data: Dict[str, Any],
    prefer: str = "best",
    show_empty: bool = False,
    stream=None,
) -> None:
    """
    Stampa "bello" il payload del servizio su stream (default stdout).
    Supporta sia document_summary.entities che document_pages[*].entities e aggregated_entities.
    """
    if stream is None:
        stream = sys.stdout

    service = data.get("service", "")
    service_name = data.get("service_name", "")
    now = data.get("current_date") or datetime.utcnow().isoformat()
    doc = data.get("document") or {}
    doc_name = doc.get("original_name", "")
    mime = doc.get("content_type", "")
    pages = doc.get("page_count", "")

    print("\n=== Documento Estratto ===", file=stream)
    print(f"Servizio       : {service_name} ({service})", file=stream)
    print(f"Data corrente  : {now}", file=stream)
    print(f"Documento      : {doc_name} | {mime} | pagine: {pages}", file=stream)

    print("\n--- Campi Estratti ---", file=stream)
    headers = ["Alias", "Chiave", "Valore", "Conf.", "Multi", "Presente"]
    rows = rows_from_payload(data, prefer=prefer, include_empty=show_empty)
    if rows:
        _print_table(headers, rows, stream=stream)
    else:
        print("(nessun campo estratto)", file=stream)


def to_markdown(
    data: Dict[str, Any],
    prefer: str = "best",
    show_empty: bool = False,
) -> str:
    headers = ["Alias", "Chiave", "Valore", "Conf.", "Multi", "Presente"]
    rows = rows_from_payload(data, prefer=prefer, include_empty=show_empty)
    out = io.StringIO()
    out.write("| " + " | ".join(headers) + " |\n")
    out.write("|" + "|".join(["---"] * len(headers)) + "|\n")
    for r in rows:
        out.write("| " + " | ".join(r) + " |\n")
    return out.getvalue()


def to_csv(
    data: Dict[str, Any],
    prefer: str = "best",
    show_empty: bool = False,
) -> str:
    headers = ["Alias", "Chiave", "Valore", "Conf.", "Multi", "Presente"]
    rows = rows_from_payload(data, prefer=prefer, include_empty=show_empty)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)
    writer.writerows(rows)
    return out.getvalue()


# ---------------------- OUTPUT LIST -> TABELLE ----------------------

def pretty_output(output, group=True, best_conf=True, sort_by="tipo", stream=None):
    """
    Stampa un 'pretty' per una lista di dict come:
      {"tipo": <alias>, "valore": <value>, "confidence": <conf>}
    Gestisce anche liste annidate di dict (es. [[{...}, {...}], {...}]).

    Args:
        output: lista (anche annidata) di dict con chiavi 'tipo', 'valore', 'confidence'
        group: se True raggruppa per 'tipo'
        best_conf: se True, in ogni gruppo mostra solo l'elemento con conf. più alta
                   (se False concatena i valori/confidence dello stesso 'tipo')
        sort_by: 'tipo' (default) oppure 'confidence' per ordinare per conf. desc
        stream: destinazione di stampa (default stdout)
    """
    if stream is None:
        stream = sys.stdout

    # --- funzione interna per appiattire qualsiasi struttura annidata ---
    def flatten_output(obj):
        """Ritorna una lista piatta di dizionari validi."""
        flattened = []
        if isinstance(obj, dict):
            if "tipo" in obj:
                flattened.append(obj)
        elif isinstance(obj, (list, tuple)):
            for elem in obj:
                flattened.extend(flatten_output(elem))
        return flattened

    flat_output = flatten_output(output)

    # Nessun dict valido
    print("\n--- Output Estratto ---", file=stream)
    if not flat_output:
        print("(output vuoto o non valido)", file=stream)
        return

    # Normalizza in (tipo, valore, conf_str)
    cleaned = []
    for item in flat_output:
        tipo = str(item.get("tipo", "")).strip()
        valore = "" if item.get("valore") is None else str(item.get("valore")).strip()
        conf_str = _fmt_conf(item.get("confidence", ""))
        cleaned.append((tipo, valore, conf_str))

    # Costruisci righe
    rows: List[List[str]] = []
    if not group:
        rows = [[t, v, c] for (t, v, c) in cleaned]
    else:
        bucket: DefaultDict[str, List[Tuple[str, str]]] = defaultdict(list)
        for t, v, c in cleaned:
            bucket[t].append((v, c))
        for t, vals in bucket.items():
            if best_conf:
                best_v, best_c, best_cf = "", "", -1.0
                for v, c in vals:
                    try:
                        cf = float(c.replace(",", ".")) if c else -1.0
                    except Exception:
                        cf = -1.0
                    if (cf > best_cf) and v.strip():
                        best_v, best_c, best_cf = v, c, cf
                rows.append([t, best_v, best_c])
            else:
                merged_v = " | ".join([v for v, _ in vals if str(v).strip()])
                merged_c = " | ".join([c for _, c in vals if c])
                rows.append([t, merged_v, merged_c])

    # Ordinamento
    if sort_by == "confidence":
        def _key_conf(r):
            c = r[2]
            if "|" in c:
                c = c.split("|", 1)[0].strip()
            try:
                return float(c.replace(",", ".")) if c else -1.0
            except Exception:
                return -1.0
        rows.sort(key=_key_conf, reverse=True)
    else:
        rows.sort(key=lambda r: (r[0] or "").lower())

    # Stampa tabella
    headers = ["Tipo", "Valore", "Conf."]
    _print_table(headers, rows, stream=stream)


def to_markdown_output(
    output,
    group: bool = True,
    best_conf: bool = True,
    sort_by: str = "tipo",
) -> str:
    """Esporta l'output (anche annidato) in tabella Markdown."""
    # Riusa pretty_output internamente per ottenere le righe in modo consistente
    # (replico la logica senza stampare)
    def flatten_output(obj):
        flattened = []
        if isinstance(obj, dict):
            if "tipo" in obj:
                flattened.append(obj)
        elif isinstance(obj, (list, tuple)):
            for elem in obj:
                flattened.extend(flatten_output(elem))
        return flattened

    flat_output = flatten_output(output)
    if not flat_output:
        return "| Tipo | Valore | Conf. |\n|---|---|---|\n| (vuoto) | | |\n"

    cleaned = []
    for item in flat_output:
        tipo = str(item.get("tipo", "")).strip()
        valore = "" if item.get("valore") is None else str(item.get("valore")).strip()
        conf_str = _fmt_conf(item.get("confidence", ""))
        cleaned.append((tipo, valore, conf_str))

    if not group:
        rows = [[t, v, c] for (t, v, c) in cleaned]
    else:
        bucket: DefaultDict[str, List[Tuple[str, str]]] = defaultdict(list)
        for t, v, c in cleaned:
            bucket[t].append((v, c))
        rows: List[List[str]] = []
        for t, vals in bucket.items():
            if best_conf:
                best_v, best_c, best_cf = "", "", -1.0
                for v, c in vals:
                    try:
                        cf = float(c.replace(",", ".")) if c else -1.0
                    except Exception:
                        cf = -1.0
                    if (cf > best_cf) and v.strip():
                        best_v, best_c, best_cf = v, c, cf
                rows.append([t, best_v, best_c])
            else:
                merged_v = " | ".join([v for v, _ in vals if str(v).strip()])
                merged_c = " | ".join([c for _, c in vals if c])
                rows.append([t, merged_v, merged_c])

    if sort_by == "confidence":
        def _key_conf(r):
            c = r[2]
            if "|" in c:
                c = c.split("|", 1)[0].strip()
            try:
                return float(c.replace(",", ".")) if c else -1.0
            except Exception:
                return -1.0
        rows.sort(key=_key_conf, reverse=True)
    else:
        rows.sort(key=lambda r: (r[0] or "").lower())

    out = io.StringIO()
    headers = ["Tipo", "Valore", "Conf."]
    out.write("| " + " | ".join(headers) + " |\n")
    out.write("|" + "|".join(["---"] * len(headers)) + "|\n")
    for r in rows:
        out.write("| " + " | ".join(r) + " |\n")
    return out.getvalue()


def to_csv_output(
    output,
    group: bool = True,
    best_conf: bool = True,
    sort_by: str = "tipo",
) -> str:
    """Esporta l'output (anche annidato) in CSV."""
    def flatten_output(obj):
        flattened = []
        if isinstance(obj, dict):
            if "tipo" in obj:
                flattened.append(obj)
        elif isinstance(obj, (list, tuple)):
            for elem in obj:
                flattened.extend(flatten_output(elem))
        return flattened

    flat_output = flatten_output(output)
    if not flat_output:
        return "Tipo,Valore,Conf.\n(vuoto),,\n"

    cleaned = []
    for item in flat_output:
        tipo = str(item.get("tipo", "")).strip()
        valore = "" if item.get("valore") is None else str(item.get("valore")).strip()
        conf_str = _fmt_conf(item.get("confidence", ""))
        cleaned.append((tipo, valore, conf_str))

    if not group:
        rows = [[t, v, c] for (t, v, c) in cleaned]
    else:
        bucket: DefaultDict[str, List[Tuple[str, str]]] = defaultdict(list)
        for t, v, c in cleaned:
            bucket[t].append((v, c))
        rows: List[List[str]] = []
        for t, vals in bucket.items():
            if best_conf:
                best_v, best_c, best_cf = "", "", -1.0
                for v, c in vals:
                    try:
                        cf = float(c.replace(",", ".")) if c else -1.0
                    except Exception:
                        cf = -1.0
                    if (cf > best_cf) and v.strip():
                        best_v, best_c, best_cf = v, c, cf
                rows.append([t, best_v, best_c])
            else:
                merged_v = " | ".join([v for v, _ in vals if str(v).strip()])
                merged_c = " | ".join([c for _, c in vals if c])
                rows.append([t, merged_v, merged_c])

    if sort_by == "confidence":
        def _key_conf(r):
            c = r[2]
            if "|" in c:
                c = c.split("|", 1)[0].strip()
            try:
                return float(c.replace(",", ".")) if c else -1.0
            except Exception:
                return -1.0
        rows.sort(key=_key_conf, reverse=True)
    else:
        rows.sort(key=lambda r: (r[0] or "").lower())

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Tipo", "Valore", "Conf."])
    writer.writerows(rows)
    return out.getvalue()
