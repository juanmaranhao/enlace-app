"""Fronteira de leitura: caminhos canônicos, sem imports do projeto observado."""
from pathlib import Path
import os

EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'staticfiles',
            'media', 'uploads', 'backups', 'backup', '.cache', '.aws',
            '.ssh', 'logs', 'dist', 'build'}

def authorized_root(value, allowed):
    root = Path(value).resolve(strict=True)
    if not root.is_dir() or not any(root.is_relative_to(Path(base).resolve()) for base in allowed):
        raise ValueError('Escolha uma pasta dentro das raízes autorizadas.')
    if any(part.lower() in EXCLUDED for part in root.parts):
        raise ValueError('Esta pasta não pode ser acompanhada.')
    return root

def safe_source(root, relative):
    """Revalida também a resolução de links/junctions no momento da leitura."""
    root = Path(root).resolve(strict=True)
    supplied = Path(relative)
    if supplied.is_absolute() or '..' in supplied.parts or any(p.lower() in EXCLUDED for p in supplied.parts):
        raise ValueError('Fonte fora do catálogo permitido.')
    source = (root / supplied).resolve(strict=True)
    if not source.is_relative_to(root) or not source.is_file():
        raise ValueError('Fonte fora do projeto.')
    return source

ROOT_DOCUMENTS = {'agents.md', 'codex.md', 'doutrina.md', 'fluxos.md', 'projeto.md',
                  'identidade.md', 'readme.md', 'design_aprovado.md'}

def catalog_path(relative):
    path = Path(relative)
    parts = tuple(p.lower() for p in path.parts)
    if not parts or path.is_absolute() or '..' in parts:
        return False
    if any(p in EXCLUDED or p.startswith('.env') for p in parts):
        return False
    if len(parts) == 1:
        return parts[0] in ROOT_DOCUMENTS
    if len(parts)==2 and parts[0]=='docs' and path.suffix.lower()=='.md':
        return parts[1].startswith('arquitetura-')
    if parts[:2] == ('.agents', 'skills'):
        return parts[-1] == 'skill.md'
    if parts[:2] == ('.codex', 'agents'):
        return len(parts) == 3 and path.suffix.lower() == '.toml'
    return (parts[:2] in {('docs', 'agentica'), ('docs', 'arquitetura'), ('docs', 'fluxos'), ('docs', 'contratos')}
            and path.suffix.lower() == '.md')

def read_source(root, relative, max_bytes=262144):
    if not catalog_path(relative):
        raise ValueError('Fonte não autorizada para leitura.')
    source = safe_source(root, relative)
    with source.open('rb') as handle:
        if os.name == 'nt':
            import ctypes
            import msvcrt
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            final_path = kernel.GetFinalPathNameByHandleW
            final_path.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
            final_path.restype = ctypes.c_uint32
            buffer = ctypes.create_unicode_buffer(32768)
            size = final_path(msvcrt.get_osfhandle(handle.fileno()), buffer, len(buffer), 0)
            if not size or size >= len(buffer):
                raise ValueError('Não foi possível confirmar a origem do arquivo.')
            value = buffer.value
            if value.startswith('\\\\?\\UNC\\'):
                value = '\\\\' + value[8:]
            elif value.startswith('\\\\?\\'):
                value = value[4:]
            final = Path(value).resolve()
        else:
            proc = Path(f'/proc/self/fd/{handle.fileno()}')
            final = proc.resolve() if proc.exists() else source.resolve()
        if not final.is_relative_to(Path(root).resolve()) or not catalog_path(final.relative_to(Path(root).resolve())):
            raise ValueError('A origem do arquivo mudou durante a leitura.')
        data = handle.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError('Fonte acima do limite de 256 KiB; não foi indexada.')
    return data.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
