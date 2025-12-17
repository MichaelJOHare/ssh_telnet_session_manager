from __future__ import annotations

import os
import select
import socket
import subprocess
from pathlib import Path
from typing import Literal

from .ansi import clear_screen, Ansi, set_title
from .prompting import prompt_text
from .types import Transport
from .config_utils import read_host_values
from .menu_utils import format_host_display


_RC_SUCCESS = 0
_RC_USERNAME_REQUIRED = 2
_RC_NO_HOSTNAME = 3
_RC_TIMEOUT = 124
_RC_CANCELLED = 130
_RC_LOOKUP_FAILURE = 255

_CONNECT_TIMEOUT_SECONDS = 10


def _parse_port(port_text: str, default: int) -> int:
    try:
        return int(port_text) if port_text else default
    except ValueError:
        return default


def _tcp_connect_with_countdown(hostname: str, port: int, timeout_seconds: int) -> int:
    """Attempt a TCP connect with a simple countdown.

    Returns:
      _RC_SUCCESS on success
      _RC_TIMEOUT on timeout
      _RC_CANCELLED on Ctrl-C
      non-zero OS error code on immediate failure
    """
    if timeout_seconds <= 0:
        timeout_seconds = 1

    try:
        # resolve once up front so obvious failures are immediate
        addrinfos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except KeyboardInterrupt:
        return _RC_CANCELLED
    except OSError:
        # DNS/lookup failures should just be treated as a failure
        return _RC_LOOKUP_FAILURE

    last_err = 1
    for family, socktype, proto, _, sockaddr in addrinfos:
        sock: socket.socket | None = None
        try:
            sock = socket.socket(family, socktype, proto)
            sock.setblocking(False)

            err = sock.connect_ex(sockaddr)
            # connect_ex may succeed immediately
            if err == 0:
                return _RC_SUCCESS

            # wait with countdown
            remaining = timeout_seconds
            display_host = f"{Ansi.GREEN}{hostname}{Ansi.RESET}:{Ansi.MAGENTA}{port}{Ansi.RESET}"
            while remaining > 0:
                print(f"\rAttempting to connect to {display_host}... timeout in {remaining:2d}s", end="", flush=True)
                try:
                    _, writable, _ = select.select([], [sock], [], 1)
                except KeyboardInterrupt:
                    print("\r", end="", flush=True)
                    return _RC_CANCELLED

                # check if socket is writable (connected)
                if writable:
                    so_error = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    if so_error == 0:
                        print("\rConnecting...                           \n", end="", flush=True)
                        return _RC_SUCCESS
                    last_err = so_error or 1
                    break
                remaining -= 1

            last_err = _RC_TIMEOUT
        except KeyboardInterrupt:
            return _RC_CANCELLED
        except OSError as e:
            last_err = getattr(e, "errno", 1) or 1
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

        if last_err == _RC_SUCCESS:
            return _RC_SUCCESS

    return last_err


# get MSYS2 ssh/telnet executable path if available, else default to windows version
def _msys2_exe(name: str) -> str:
    usr_bin = os.environ.get("MSYS2_USR_BIN")
    if usr_bin:
        candidate = Path(usr_bin) / f"{name}.exe"
        if candidate.exists():
            return str(candidate)
    return name


def ssh_connect(host_alias: str, transport: Transport, *, 
                timeout_seconds: int = _CONNECT_TIMEOUT_SECONDS) -> int:
    try:
        user = prompt_text(f"{Ansi.MAGENTA}login{Ansi.RESET} as: ").strip()
    except KeyboardInterrupt:
        return _RC_CANCELLED
    if not user:
        return _RC_USERNAME_REQUIRED

    clear_screen()
    display_host = format_host_display(host_alias)
    print(f"Connecting to {display_host} as {Ansi.MAGENTA}{user}{Ansi.RESET}...")
    set_title(f"{user}@{host_alias}")
    try:
        hostname, port_text, *_ = read_host_values(host_alias, transport.config_file)
        if hostname:
            port = _parse_port(port_text, 22)
            rc = _tcp_connect_with_countdown(hostname, port, timeout_seconds)
            if rc != _RC_SUCCESS:
                print()
                return rc

        ssh_exe = _msys2_exe("ssh")
        try:
            ssh_args = [ssh_exe, "-o", f"ConnectTimeout={timeout_seconds}", f"{user}@{host_alias}"]
            result = subprocess.run(ssh_args)
            return result.returncode
        except KeyboardInterrupt:
            return _RC_CANCELLED
    finally:
        set_title("VMS MENU")


def telnet_connect(host_alias: str, config_file: Path, *, 
                   timeout_seconds: int = _CONNECT_TIMEOUT_SECONDS) -> int:
    hostname, port, *_ = read_host_values(host_alias, config_file)
    if not hostname:
        return _RC_NO_HOSTNAME
    clear_screen()
    display_host = format_host_display(host_alias)
    print(f"Connecting to {display_host} via telnet...")
    set_title(f"telnet:{host_alias}")
    try:
        rc = _tcp_connect_with_countdown(hostname, _parse_port(port, 23), timeout_seconds)
        if rc != _RC_SUCCESS:
            print()
            return rc
        telnet_exe = _msys2_exe("telnet")
        try:
            result = subprocess.run([telnet_exe, hostname, str(port or "23")])
            return result.returncode
        except KeyboardInterrupt:
            return _RC_CANCELLED
    finally:
        set_title("VMS MENU")


def attempt_connection(host_label: str, transport: Transport, *, 
                       last_msg_out: list[str]) -> bool:
    timeout_seconds = _CONNECT_TIMEOUT_SECONDS

    if transport.key == "ssh":
        rc = ssh_connect(host_label, transport, timeout_seconds=timeout_seconds)
        msg = _message_for_connect_rc(
            rc, host_label, protocol="ssh", timeout_seconds=timeout_seconds
        )
    else:
        rc = telnet_connect(host_label, transport.config_file, timeout_seconds=timeout_seconds)
        msg = _message_for_connect_rc(
            rc, host_label, protocol="telnet", timeout_seconds=timeout_seconds
        )

    last_msg_out[:] = [""] if msg is None else msg
    return rc == _RC_SUCCESS


def _message_for_connect_rc(
    rc: int,
    host_label: str,
    *,
    protocol: Literal["ssh", "telnet"],
    timeout_seconds: int,
) -> list[str] | None:
    """Map a connection return code to a menu message.

    Returns None for success (meaning: clear last message).
    """
    if rc == _RC_SUCCESS:
        return None
    if rc == _RC_CANCELLED:
        return ["Cancelled connection attempt"]
    if rc == _RC_TIMEOUT:
        return [f"Connection timed out after {timeout_seconds}s"]
    if rc == _RC_LOOKUP_FAILURE:
        return [f"Could not resolve hostname for {Ansi.GREEN}{host_label}{Ansi.RESET}"]

    if protocol == "ssh" and rc == _RC_USERNAME_REQUIRED:
        return ["Error: username required"]
    if protocol == "telnet" and rc == _RC_NO_HOSTNAME:
        return [
            f"No telnet hostname/IP configured for {Ansi.GREEN}{host_label}{Ansi.RESET}\n"
            f"{Ansi.YELLOW}Note{Ansi.RESET}: ~/.telnet/config should have an empty newline at the end of the file."
        ]

    return [f"Connection to {host_label} failed — returned to menu"]