from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from typing import Iterator

from django.conf import settings

from apps.integracao.models import FirebirdConnectionConfig


ALLOWED_FIREBIRD_EXTENSIONS = {".fdb", ".gdb", ".fbk"}


def _get_env_default_path() -> str:
    return str(getattr(settings, "FDB_PATH", "") or "").strip()


def _normalize_candidate_path(raw_path: str) -> str:
    expanded = os.path.expanduser(str(raw_path or "").strip())
    if not expanded:
        return ""
    return os.path.abspath(expanded)


def _is_allowed_firebird_file(path: str) -> bool:
    extension = os.path.splitext(str(path or ""))[1].lower()
    return extension in ALLOWED_FIREBIRD_EXTENSIONS


def validate_firebird_path(raw_path: str) -> str:
    candidate = _normalize_candidate_path(raw_path)
    if not candidate:
        raise ValueError("Nenhum caminho Firebird informado.")
    if not _is_allowed_firebird_file(candidate):
        raise ValueError("Arquivo invalido. Selecione um arquivo Firebird (.fdb, .gdb ou .fbk).")
    if not os.path.isfile(candidate):
        raise ValueError("Arquivo Firebird informado nao foi encontrado.")
    return candidate


def get_firebird_connection_config() -> FirebirdConnectionConfig:
    config = FirebirdConnectionConfig.get_solo()
    if not config.caminho_fixo:
        fallback = _get_env_default_path()
        if fallback:
            config.caminho_fixo = fallback
            config.save(update_fields=["caminho_fixo", "atualizado_em"])
    return config


def serialize_firebird_connection_config(config: FirebirdConnectionConfig) -> dict:
    caminho_fixo = str(config.caminho_fixo or "").strip()
    caminho_efetivo = caminho_fixo or _get_env_default_path()
    return {
        "modo_localizacao": config.modo_localizacao,
        "caminho_fixo": caminho_fixo,
        "caminho_efetivo": caminho_efetivo,
        "usa_fallback_env": bool(not caminho_fixo and caminho_efetivo),
    }


def _persist_uploaded_firebird(uploaded_file) -> str:
    extension = os.path.splitext(str(getattr(uploaded_file, "name", "") or ""))[1]
    suffix = extension if extension else ".fdb"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        return temp_file.name


def pick_firebird_file_via_os_dialog() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise RuntimeError("Nao foi possivel abrir o explorer neste ambiente.") from exc

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(
            title="Selecione o arquivo Firebird",
            filetypes=[
                ("Firebird", "*.fdb *.gdb *.fbk"),
                ("Todos os arquivos", "*.*"),
            ],
        )
    except Exception as exc:
        raise RuntimeError("Nao foi possivel abrir o explorer neste ambiente.") from exc
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass

    return str(selected or "").strip()


@contextmanager
def resolve_firebird_path_for_request(request) -> Iterator[str]:
    config = get_firebird_connection_config()
    temp_file_path = None

    if config.modo_localizacao == FirebirdConnectionConfig.MODO_DINAMICO:
        dynamic_path = str(request.data.get("firebird_path") or "").strip()
        if dynamic_path:
            resolved_path = validate_firebird_path(dynamic_path)
        else:
            uploaded_file = request.FILES.get("firebird_file")
            if uploaded_file is None:
                raise ValueError(
                    "Modo dinamico ativo. Selecione o arquivo Firebird antes de iniciar a sincronizacao."
                )
            temp_file_path = _persist_uploaded_firebird(uploaded_file)
            resolved_path = temp_file_path
    else:
        caminho_fixo = str(config.caminho_fixo or "").strip()
        resolved_path = caminho_fixo or _get_env_default_path()
        if not resolved_path:
            raise ValueError(
                "Nenhum caminho Firebird configurado. Defina um caminho fixo no Painel do Sistema."
            )

    try:
        yield resolved_path
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
