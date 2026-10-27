"""Inventário Git limitado a metadados; nunca altera ou limpa o repositório."""
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import subprocess
from threading import Thread

from .paths import authorized_root


class GitInventoryError(ValueError):
    """O Git não confirmou um inventário completo e confiável."""


_QUERIES = {
    "git_dir": ("rev-parse", "--absolute-git-dir"),
    "head": ("rev-parse", "--verify", "HEAD"),
    "branch": ("symbolic-ref", "--quiet", "--short", "HEAD"),
    "status": ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=all"),
    "ignored": ("ls-files", "--others", "--ignored", "--exclude-standard", "-z"),
    "flags": ("ls-files", "-v", "-z"),
    "worktrees": ("worktree", "list", "--porcelain", "-z"),
}
MAX_OUTPUT = 8 * 1024 * 1024


def _query(executable, root, name, timeout, git_dir=None):
    """Somente consultas enumeradas; nenhuma string é interpretada por shell."""
    args = [executable, "--no-optional-locks", "-c", "core.fsmonitor=false",
            "-c", "core.untrackedCache=false", "-c", f"safe.directory={root}"]
    if git_dir:
        args.extend([f"--git-dir={git_dir}", f"--work-tree={root}"])
    else:
        args.extend(["-C", str(root)])
    args.extend(_QUERIES[name])
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_PAGER="cat")
    try:
        process = subprocess.Popen(args, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as exc:
        raise GitInventoryError("Git indisponível ou consulta excedeu o tempo permitido.") from exc
    data = bytearray()
    exceeded = []

    def read_bounded():
        while chunk := process.stdout.read(65536):
            if len(data) + len(chunk) > MAX_OUTPUT:
                exceeded.append(True)
                process.kill()
                return
            data.extend(chunk)

    reader = Thread(target=read_bounded, daemon=True)
    reader.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait(timeout=3)
        raise GitInventoryError("Git excedeu o tempo permitido; observação não concluída.") from exc
    finally:
        reader.join(timeout=3)
        process.stdout.close()
    if exceeded:
        raise GitInventoryError("Inventário acima do limite; nenhum resultado parcial foi aprovado.")
    if process.returncode and not (name == "branch" and process.returncode == 1):
        raise GitInventoryError("O Git não confirmou a consulta. Confira a pasta e as permissões.")
    return data.decode("utf-8", errors="replace")


def _status_counts(raw):
    """Porcelain -z inclui dois nomes para rename/copy; não duplica a contagem."""
    tracked = untracked = 0
    records = iter(raw.split("\0"))
    for record in records:
        if not record:
            continue
        if record.startswith("?? "):
            untracked += 1
        else:
            tracked += 1
            if "R" in record[:2] or "C" in record[:2]:
                next(records, None)
    return tracked, untracked


def _worktrees(raw, allowed_roots):
    rows = []
    current = {}
    for record in raw.split("\0"):
        if not record:
            if current:
                rows.append(current)
                current = {}
            continue
        key, _, value = record.partition(" ")
        if key == "worktree":
            try:
                path = authorized_root(value, allowed_roots)
                current = {"path": str(path), "authorized": True}
            except (OSError, ValueError):
                current = {"path": None, "authorized": False}
        elif key == "HEAD":
            current["head"] = value[:64]
        elif key == "branch":
            current["branch"] = value.removeprefix("refs/heads/")[:200]
        elif key in {"bare", "detached", "locked", "prunable"}:
            current[key] = True
    if current:
        rows.append(current)
    return rows[:200]


def inspect_repository(root, allowed_roots, *, timeout=15, executable=None):
    """Retorna observação datada; o resultado jamais concede permissão de descarte.

    ``allowed_roots`` é fornecido pela instalação, nunca pelo pedido de um agente.
    A ponte .git pode apontar para gitdir externo, mas o work-tree sempre é explícito.
    Não há leitura de conteúdo dos arquivos alterados, ignorados ou não rastreados.
    """
    root = authorized_root(root, allowed_roots)
    executable = executable or shutil.which("git")
    if not executable:
        raise GitInventoryError("Git não está instalado ou não está disponível no PATH.")
    git_dir = _query(executable, root, "git_dir", timeout).strip()
    if not git_dir or not Path(git_dir).is_absolute():
        raise GitInventoryError("Diretório Git não confirmado.")
    values = {name: _query(executable, root, name, timeout, git_dir)
              for name in ("head", "branch", "status", "ignored", "flags", "worktrees")}
    tracked, untracked = _status_counts(values["status"])
    ignored = sum(bool(value) for value in values["ignored"].split("\0"))
    hidden = sum(bool(value) and (value[0].islower() or value[0] == "S")
                 for value in values["flags"].split("\0"))
    return {
        "schema_version": 1, "read_only": True,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root), "head": values["head"].strip()[:64],
        "branch": values["branch"].strip()[:200] or None,
        "tracked_changed": tracked, "untracked_count": untracked,
        "ignored_count": ignored, "hidden_index_flags": hidden,
        "dirty": bool(tracked or untracked or hidden),
        "worktrees": _worktrees(values["worktrees"], allowed_roots),
        "cleanup_authorized": False,
        "retention": "preserve",
        "limitations": ["Sem consulta remota ou prova de integração de PR.",
                        "Ignorados e arquivos exclusivos permanecem preservados.",
                        "Consultas sequenciais; alterações concorrentes podem mudar o estado."],
    }
