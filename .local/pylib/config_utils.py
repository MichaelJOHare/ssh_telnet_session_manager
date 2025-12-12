from __future__ import annotations

import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

from .types import HostEntry


GROUP_DELIMITER = "."


_HOST_EXACT_RE = re.compile(r"^Host\s+(?P<alias>[^\s]+)\s*$")
_HOST_ANY_RE = re.compile(r"^Host\s+(?P<aliases>.+)$")
_KEYVAL_RE = re.compile(r"^\s*(?P<key>[A-Za-z][A-Za-z0-9]*)\s+(?P<value>.+?)\s*$")


def load_host_aliases(config_file: Path) -> list[str]:
    aliases: list[str] = []
    if not config_file.exists():
        return aliases

    for line in config_file.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _HOST_ANY_RE.match(line)
        if not m:
            continue
        for alias in m.group("aliases").split():
            aliases.append(alias)
    return aliases


def list_groups(config_file: Path, *, delimiter: str = GROUP_DELIMITER) -> list[str]:
    groups: set[str] = set()
    for alias in load_host_aliases(config_file):
        if delimiter in alias:
            group = alias.split(delimiter, 1)[0].lower()
            if group and re.fullmatch(r"[a-z0-9]+", group):
                groups.add(group)
    return sorted(groups)


def find_aliases_for_nickname(nickname_upper: str, config_file: Path, *, delimiter: str = GROUP_DELIMITER) -> list[str]:
    needle = nickname_upper.upper()
    matches: list[str] = []
    for alias in load_host_aliases(config_file):
        if alias.upper() == needle:
            matches.append(alias)
            continue
        if delimiter in alias:
            member = alias.split(delimiter, 1)[1].upper()
            if member == needle:
                matches.append(alias)
    return matches


def host_entry_exists(alias: str, config_file: Path) -> bool:
    if not config_file.exists():
        return False
    text = config_file.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        m = _HOST_EXACT_RE.match(line)
        if m and m.group("alias") == alias:
            return True
    return False


def read_host_values(alias: str, config_file: Path) -> tuple[str, str, str, str, str]:
    hostname = ""
    port = ""
    hostkey = ""
    kex = ""
    macs = ""

    in_block = False
    for raw_line in config_file.read_text(encoding="utf-8", errors="replace").splitlines():
        host_m = _HOST_ANY_RE.match(raw_line)
        if host_m:
            # block starts only if the Host line is exactly "Host <alias>"
            exact = _HOST_EXACT_RE.match(raw_line)
            if exact and exact.group("alias") == alias:
                in_block = True
                continue
            if in_block:
                break

        if not in_block:
            continue

        kv = _KEYVAL_RE.match(raw_line)
        if not kv:
            continue
        key = kv.group("key").lower()
        value = kv.group("value")
        if key == "hostname":
            hostname = value
        elif key == "port":
            port = value
        elif key == "hostkeyalgorithms":
            hostkey = value
        elif key == "kexalgorithms":
            kex = value
        elif key == "macs":
            macs = value

    return hostname, port, hostkey, kex, macs


def remove_host_entry(alias: str, config_file: Path) -> None:
    if not config_file.exists():
        return

    lines = config_file.read_text(encoding="utf-8", errors="replace").splitlines(True)

    out: list[str] = []
    skip = False
    for line in lines:
        exact = _HOST_EXACT_RE.match(line.rstrip("\n"))
        any_host = _HOST_ANY_RE.match(line.rstrip("\n"))

        if any_host:
            if skip:
                skip = False
            if exact and exact.group("alias") == alias:
                skip = True
                continue

        if skip:
            continue
        out.append(line)

    _atomic_write_text(config_file, "".join(out))


def append_host_entry(entry: HostEntry, config_file: Path) -> None:
    prefix = ""
    if config_file.exists() and config_file.stat().st_size > 0:
        text = config_file.read_text(encoding="utf-8", errors="replace")
        # Only add a leading blank line if the file doesn't already end with one.
        if not text.endswith("\n"):
            prefix = "\n"
        else:
            # if last line isn't blank, add a blank line
            if not text.endswith("\n\n"):
                prefix = "\n"

    block_lines = [
        f"{prefix}Host {entry.alias}\n",
        f"    Hostname {entry.hostname}\n",
        f"    Port {entry.port}\n",
    ]

    if entry.hostkey_algorithms:
        block_lines.append(f"    HostKeyAlgorithms {entry.hostkey_algorithms}\n")
    if entry.kex_algorithms:
        block_lines.append(f"    KexAlgorithms {entry.kex_algorithms}\n")
    if entry.macs:
        block_lines.append(f"    MACs {entry.macs}\n")

    with config_file.open("a", encoding="utf-8", newline="") as f:
        f.writelines(block_lines)


def upsert_host_entry(entry: HostEntry, config_file: Path) -> None:
    remove_host_entry(entry.alias, config_file)
    append_host_entry(entry, config_file)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, encoding="utf-8", newline="") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def split_hosts_by_group(
    hosts: Iterable[str], *, delimiter: str = GROUP_DELIMITER
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    main_hosts: list[str] = []
    grouped: dict[str, list[str]] = {}

    for host in hosts:
        if delimiter in host:
            group, member = host.split(delimiter, 1)
            if group and member and re.fullmatch(r"[a-z0-9]+", group):
                grouped.setdefault(group, []).append(host)
                continue
        main_hosts.append(host)

    main_hosts = sorted(main_hosts, key=str.casefold)
    group_names = sorted(grouped.keys())
    for g in group_names:
        grouped[g] = sorted(grouped[g], key=str.casefold)

    return main_hosts, grouped, group_names
