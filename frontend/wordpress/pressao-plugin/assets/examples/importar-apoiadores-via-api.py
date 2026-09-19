#!/usr/bin/env python3
"""
Importa candidatos apoiadores via REST (um PUT por linha do CSV).

Pré-requisito: Application Password de um usuário com manage_options.
Colunas iguais ao CSV do admin: nome, cargo, partido, descricao, instagram (ou link_url),
imagem_url (opcional).

Uso:
  export WP_URL="https://seu-site.exemplo"
  export WP_USER="admin"
  export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
  python3 importar-apoiadores-via-api.py candidatos-apoiadores-exemplo.csv

Opções:
  --dry-run     só valida/parseia, não chama a API
  --sleep 0.2   pausa entre requests (segundos)
  --start 1     número da primeira linha de dados (1 = após header)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from base64 import b64encode
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


HEADER_ALIASES = {
    "nome": ("nome", "name"),
    "cargo": ("cargo", "role"),
    "partido": ("partido", "partido_organizacao", "partido/organizacao", "organizacao"),
    "descricao": ("descricao", "descrição", "description"),
    "instagram": ("instagram", "link_url", "handle", "@"),
    "imagem_url": ("imagem_url", "imagem", "image_url", "image", "foto", "foto_url"),
}


def normalize_header(h: str) -> str:
    return h.strip().lower().replace(" ", "_").replace("-", "_")


def detect_delimiter(header_line: str) -> str:
    return ";" if header_line.count(";") > header_line.count(",") else ","


def map_columns(headers: List[str]) -> Dict[str, int]:
    norm = [normalize_header(h) for h in headers]
    col: Dict[str, int] = {}
    for key, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in norm:
                col[key] = norm.index(alias)
                break
    return col


def cell(row: List[str], col: Dict[str, int], key: str) -> str:
    if key not in col:
        return ""
    idx = col[key]
    if idx >= len(row):
        return ""
    return (row[idx] or "").strip()


def basic_auth(user: str, password: str) -> str:
    token = b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def api_request(
    method: str,
    url: str,
    auth_header: str,
    body: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> Tuple[int, Any]:
    data = None
    headers = {
        "Authorization": auth_header,
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else None
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {"message": raw}
        except json.JSONDecodeError:
            payload = {"message": raw}
        return exc.code, payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="Caminho do CSV")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.0, help="Pausa entre PUTs (s)")
    parser.add_argument("--start", type=int, default=1, help="Primeira linha de dados (1-based após header)")
    args = parser.parse_args()

    wp_url = os.environ.get("WP_URL", "").rstrip("/")
    wp_user = os.environ.get("WP_USER", "")
    wp_pass = os.environ.get("WP_APP_PASSWORD", "")

    if not args.dry_run and (not wp_url or not wp_user or not wp_pass):
        print("Defina WP_URL, WP_USER e WP_APP_PASSWORD.", file=sys.stderr)
        return 2

    if not args.csv_path.is_file():
        print(f"CSV não encontrado: {args.csv_path}", file=sys.stderr)
        return 2

    text = args.csv_path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines:
        print("CSV vazio.", file=sys.stderr)
        return 2

    delimiter = detect_delimiter(lines[0])
    reader = csv.reader(lines, delimiter=delimiter)
    headers = next(reader)
    col = map_columns(headers)
    if "instagram" not in col:
        print("CSV precisa de coluna instagram (ou link_url).", file=sys.stderr)
        return 2

    endpoint = f"{wp_url}/wp-json/pressao/v1/candidatos-apoiadores"
    auth = basic_auth(wp_user, wp_pass) if not args.dry_run else ""

    ok = 0
    fail = 0
    row_num = 0

    for row in reader:
        row_num += 1
        if row_num < args.start:
            continue
        if not any((c or "").strip() for c in row):
            continue

        instagram = cell(row, col, "instagram")
        if not instagram:
            print(f"Linha {row_num}: Instagram ausente — pulando")
            fail += 1
            continue

        body: Dict[str, Any] = {"instagram": instagram}
        for key in ("nome", "cargo", "partido", "descricao"):
            val = cell(row, col, key)
            if val != "":
                body[key] = val
        imagem_url = cell(row, col, "imagem_url")
        if imagem_url:
            body["imagem_url"] = imagem_url

        if args.dry_run:
            print(f"Linha {row_num}: OK (dry-run) {instagram} {json.dumps(body, ensure_ascii=False)}")
            ok += 1
            continue

        status, payload = api_request("PUT", endpoint, auth, body)
        action = ""
        if isinstance(payload, dict):
            action = payload.get("action", "")
            warning = payload.get("warning")
        else:
            warning = None

        if 200 <= status < 300:
            warn_txt = f" warning={warning}" if warning else ""
            print(f"Linha {row_num}: {status} {action or 'ok'} {instagram}{warn_txt}")
            ok += 1
        else:
            print(f"Linha {row_num}: ERRO {status} {instagram} {payload}", file=sys.stderr)
            fail += 1

        if args.sleep > 0:
            time.sleep(args.sleep)

    print(f"Concluído: {ok} ok, {fail} falhas")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
