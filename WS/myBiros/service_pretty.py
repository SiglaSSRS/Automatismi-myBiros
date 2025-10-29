# service_pretty.py
# -*- coding: utf-8 -*-

"""
Pretty printer per payload di estrazione documentale.
Nessuna dipendenza esterna (solo standard library).


# main.py (o dove ti serve)
from service_pretty import pretty_service_response, to_markdown, to_csv

payload = {
    # ... il dizionario che ricevi ...
}

# Stampa “bello” a video (solo best)
pretty_service_response(payload, prefer="best")

# Mostra tutti i valori (se ci sono duplicati/varianti)
pretty_service_response(payload, prefer="all")

# Includi anche i campi senza valore estratto
pretty_service_response(payload, prefer="best", show_empty=True)

# Se vuoi salvare un report Markdown
md = to_markdown(payload, prefer="best")
with open("estrazione.md", "w", encoding="utf-8") as f:
    f.write(md)

# Se vuoi un CSV
csv_text = to_csv(payload, prefer="all")
with open("estrazione.csv", "w", encoding="utf-8", newline="") as f:
    f.write(csv_text)

"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple, Union
import csv
import io
import sys

__all__ = [
    "pretty_service_response",
    "rows_from_payload",
    "to_markdown",
    "to_csv",
]

Entity = Union[Dict[str, Any], str, float, int]


# ---------------------- UTIL ----------------------

def _as_list(v: Any) -> List[Entity]:
    """Normalizza in lista: [], [..], dict singolo, o valore primitivo."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def _best_entity(entities: List[Entity]) -> Tuple[str, Union[float, None]]:
    """Seleziona l'entità con confidence più alta: (text, confidence)."""
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
        # max 2 decimali, niente zeri superflui
        s = f"{float(conf):.2f}"
        # normalizza virgola/punto indipendentemente da locale
        s = s.replace(",", ".")
        return s.rstrip("0").rstrip(".")
    except Exception:
        return str(conf)


def _print_table(headers: List[str], rows: List[List[str]], stream=None) -> None:
    """Stampa una tabella ASCII con larghezze auto-calcolate."""
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


# ---------------------- API PUBBLICA ----------------------

def rows_from_payload(
    data: Dict[str, Any],
    prefer: str = "best",
    include_empty: bool = False,
) -> List[List[str]]:
    """
    Crea righe tabellari a partire dal payload.

    Ritorna una lista di righe:
    [Alias, Chiave, Valore, Conf., Multi, Presente]
    """
    service_fields = data.get("service_fields", {}) or {}
    entities = (((data.get("document_summary") or {}).get("entities")) or {})
    rows: List[List[str]] = []

    all_keys = sorted(set(service_fields.keys()) | set(entities.keys()))

    for key in all_keys:
        field_meta = service_fields.get(key, {})
        alias = field_meta.get("tag_alias", key)
        multi = field_meta.get("tag_multiple_values", False)

        raw_vals = entities.get(key, [])
        items = _as_list(raw_vals)

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
                    confs.append(c)
            if texts:
                present = "Sì"
            value_str = " | ".join(texts)
            conf_str = " | ".join([c for c in confs if c])

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

    Args:
        data: il dict payload
        prefer: "best" (default) o "all"
        show_empty: se False nasconde i campi senza valore
        stream: file-like (es. sys.stdout, file aperto, io.StringIO, ecc.)
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
    """Ritorna una tabella Markdown (stringa) con i campi estratti."""
    headers = ["Alias", "Chiave", "Valore", "Conf.", "Multi", "Presente"]
    rows = rows_from_payload(data, prefer=prefer, include_empty=show_empty)

    out = io.StringIO()
    # header
    out.write("| " + " | ".join(headers) + " |\n")
    out.write("|" + "|".join(["---"] * len(headers)) + "|\n")
    # rows
    for r in rows:
        out.write("| " + " | ".join(r) + " |\n")
    return out.getvalue()


def to_csv(
    data: Dict[str, Any],
    prefer: str = "best",
    show_empty: bool = False,
) -> str:
    """Ritorna CSV (stringa) con i campi estratti."""
    headers = ["Alias", "Chiave", "Valore", "Conf.", "Multi", "Presente"]
    rows = rows_from_payload(data, prefer=prefer, include_empty=show_empty)

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)
    writer.writerows(rows)
    return out.getvalue()

#---------------------- PRETTY OUTPUT GENERICO ----------------------   
# pretty_output(output)

def pretty_output(output, group=True, best_conf=True, sort_by="tipo", stream=None):
    """
    Stampa un 'pretty' per una lista di dict come:
      {"tipo": <alias>, "valore": <value>, "confidence": <conf>}

    Args:
        output: lista di dizionari con chiavi 'tipo', 'valore', 'confidence'
        group: se True raggruppa per 'tipo'
        best_conf: se True, in ogni gruppo mostra solo l'elemento con conf. più alta
                   (se False concatena i valori/confidence dello stesso 'tipo')
        sort_by: 'tipo' (default) oppure 'confidence' per ordinare per conf. desc
        stream: destinazione di stampa (default stdout)
    """
    import sys
    from collections import defaultdict

    if stream is None:
        stream = sys.stdout

    # Normalizza input -> (tipo, valore, conf_str)
    cleaned = []
    for item in (output or []):
        tipo = str(item.get("tipo", "")).strip()
        valore = "" if item.get("valore") is None else str(item.get("valore")).strip()
        conf_str = _fmt_conf(item.get("confidence", ""))
        cleaned.append((tipo, valore, conf_str))

    # Costruisci righe
    rows = []
    if not group:
        rows = [[t, v, c] for (t, v, c) in cleaned]
    else:
        bucket = defaultdict(list)  # tipo -> [(valore, conf_str)]
        for t, v, c in cleaned:
            bucket[t].append((v, c))

        for t, vals in bucket.items():
            if best_conf:
                # prendi il valore con conf. più alta (se manca, -1)
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
    print("\n--- Output Estratto ---", file=stream)
    if rows:
        headers = ["Tipo", "Valore", "Conf."]
        _print_table(headers, rows, stream=stream)
    else:
        print("(output vuoto)", file=stream)
