"""DRC / LVS / Spectre 실행 스켈레톤.

기본 동작은 dry-run입니다. 실제 도구를 실행하려면 --exec를 붙이세요.
사이트마다 PVS/Assura/Spectre CLI 인자가 다르므로, 이 파일은 "명령 조립 +
로그 파싱" 뼈대만 제공합니다. 실제 runset 경로와 옵션은 --pdk-root,
--drc-rules, --lvs-rules, --netlist로 조정하세요.

사용 예:
    python verify.py --cell NAND2 --mode drc
    python verify.py --cell NAND2 --mode all --pdk-root /path/to/gpdk045_v_6_0 --exec
    python verify.py --cell NAND2 --mode sim --netlist sim/NAND2.scs --exec
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ERROR_PATTERNS = ("ERROR", "Error", "Mismatch", "mismatch", "FAILED", "failed")


def find_tool(*names: str) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def run(cmd: list[str], log_path: Path, execute: bool) -> int:
    print("[CMD]", " ".join(cmd))
    if not execute:
        print("[DRY]", f"would write log to {log_path}")
        return 0

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", errors="replace") as handle:
        proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT)
    print(f"[LOG] {log_path} (exit={proc.returncode})")
    return proc.returncode


def scan_log(log_path: Path) -> list[str]:
    if not log_path.exists():
        return []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return [
        line.strip()
        for line in text.splitlines()
        if any(pattern in line for pattern in ERROR_PATTERNS)
    ]


def stream_out(lib: str, cell: str, gds: Path, execute: bool) -> int:
    tool = find_tool("strmout")
    if not tool:
        print("[SKIP] strmout not found in PATH")
        return 0
    cmd = [
        tool,
        "-library",
        lib,
        "-strmFile",
        str(gds),
        "-topCell",
        cell,
        "-view",
        "layout",
    ]
    return run(cmd, Path("logs") / f"{cell}.strmout.log", execute)


def drc(cell: str, gds: Path, rules: Path, execute: bool) -> int:
    pvs = find_tool("pvs")
    assura = find_tool("assura")

    if pvs:
        cmd = [pvs, "-drc", str(rules), "-gds", str(gds), "-top", cell]
    elif assura:
        cmd = [assura, str(rules)]
    else:
        print("[SKIP] neither pvs nor assura found in PATH")
        return 0

    return run(cmd, Path("logs") / f"{cell}.drc.log", execute)


def lvs(cell: str, gds: Path, rules: Path, execute: bool) -> int:
    pvs = find_tool("pvs")
    assura = find_tool("assura")

    if pvs:
        cmd = [pvs, "-lvs", str(rules), "-gds", str(gds), "-top", cell]
    elif assura:
        cmd = [assura, str(rules)]
    else:
        print("[SKIP] neither pvs nor assura found in PATH")
        return 0

    return run(cmd, Path("logs") / f"{cell}.lvs.log", execute)


def sim(cell: str, netlist: Path, execute: bool) -> int:
    spectre = find_tool("spectre")
    if not spectre:
        print("[SKIP] spectre not found in PATH")
        return 0
    if not netlist.exists():
        print(f"[SKIP] netlist not found: {netlist}")
        return 0

    cmd = [spectre, str(netlist), "+log", f"logs/{cell}.spectre"]
    return run(cmd, Path("logs") / f"{cell}.sim.log", execute)


def main() -> None:
    parser = argparse.ArgumentParser(description="DRC/LVS/Spectre skeleton")
    parser.add_argument("--cell", required=True, help="cell name, e.g. NAND2")
    parser.add_argument(
        "--mode",
        choices=("drc", "lvs", "sim", "all"),
        default="all",
        help="which check to run",
    )
    parser.add_argument("--lib", default="EDU45", help="Virtuoso library name")
    parser.add_argument(
        "--gds",
        default=None,
        help="GDS path (default: out/<cell>.gds)",
    )
    parser.add_argument(
        "--pdk-root",
        default=".",
        help="GPDK045 install root containing pvs/ and assura/",
    )
    parser.add_argument(
        "--drc-rules",
        default=None,
        help="DRC runset (default: <pdk-root>/pvs/pvlDRC.rul)",
    )
    parser.add_argument(
        "--lvs-rules",
        default=None,
        help="LVS runset (default: <pdk-root>/pvs/pvlLVS.rul)",
    )
    parser.add_argument(
        "--netlist",
        default=None,
        help="Spectre netlist (default: sim/<cell>.scs)",
    )
    parser.add_argument(
        "--stream-out",
        action="store_true",
        help="run strmout before DRC/LVS",
    )
    parser.add_argument(
        "--exec",
        action="store_true",
        help="actually execute commands (default: dry-run)",
    )
    args = parser.parse_args()

    cell = args.cell
    pdk_root = Path(args.pdk_root)
    gds = Path(args.gds) if args.gds else Path("out") / f"{cell}.gds"
    drc_rules = (
        Path(args.drc_rules)
        if args.drc_rules
        else pdk_root / "pvs" / "pvlDRC.rul"
    )
    lvs_rules = (
        Path(args.lvs_rules)
        if args.lvs_rules
        else pdk_root / "pvs" / "pvlLVS.rul"
    )
    netlist = Path(args.netlist) if args.netlist else Path("sim") / f"{cell}.scs"

    if args.stream_out or args.mode in ("drc", "lvs", "all"):
        print("== stream out ==")
        stream_out(args.lib, cell, gds, args.exec)

    exit_code = 0
    logs: list[Path] = []

    if args.mode in ("drc", "all"):
        print("== DRC ==")
        code = drc(cell, gds, drc_rules, args.exec)
        exit_code |= code
        logs.append(Path("logs") / f"{cell}.drc.log")

    if args.mode in ("lvs", "all"):
        print("== LVS ==")
        code = lvs(cell, gds, lvs_rules, args.exec)
        exit_code |= code
        logs.append(Path("logs") / f"{cell}.lvs.log")

    if args.mode in ("sim", "all"):
        print("== Spectre ==")
        code = sim(cell, netlist, args.exec)
        exit_code |= code
        logs.append(Path("logs") / f"{cell}.sim.log")

    print("== summary ==")
    for log in logs:
        hits = scan_log(log)
        if hits:
            print(f"[WARN] {log}: {len(hits)} suspicious line(s)")
            for line in hits[:10]:
                print("   ", line)
        else:
            print(f"[OK] {log}: no obvious error pattern")

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
