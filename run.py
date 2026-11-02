"""CDL 생성 + Virtuoso layout 생성 드라이버.

사용 예:
    # CDL만 생성 (Virtuoso/Python 브리지 불필요)
    python run.py --no-layout

    # CDL + layout (Virtuoso와 같은 Linux 호스트에서 실행)
    python run.py

    # 특정 셀만
    python run.py --only NAND2,NOR2,INV
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cells import LIB, all_specs, cdl


def write_cdl(specs, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        path = out_dir / f"{spec.name}.cdl"
        path.write_text(cdl(spec), encoding="utf-8")
        print(f"[CDL] {path}")


def make_layouts(specs, lib: str, pitch: float) -> None:
    try:
        from skillbridge import Workspace
    except ImportError as exc:
        raise SystemExit(
            "skillbridge is not installed.\n"
            "  python3 -m pip install -r requirements.txt\n"
            "  Run this on the same Linux host as Virtuoso."
        ) from exc

    ws = Workspace.open()

    for spec in specs:
        if not spec.has_layout:
            print(f"[SKIP] {spec.name}: layout template not implemented yet.")
            continue

        print(
            f"[LAY] {spec.name} "
            f"(kind={spec.kind}, n={spec.n}, wn={spec.wn}, wp={spec.wp})"
        )
        ws.EDU_make_layout(
            lib,
            spec.name,
            spec.kind,
            spec.n,
            spec.wn,
            spec.wp,
            spec.l,
            pitch,
        )
        print(f"[LAY] {spec.name} done")


def main() -> None:
    parser = argparse.ArgumentParser(description="GPDK045 cell generator")
    parser.add_argument("--lib", default=LIB, help="Virtuoso 대상 라이브러리")
    parser.add_argument("--out", default="cdl", help="CDL 출력 디렉토리")
    parser.add_argument(
        "--no-layout",
        action="store_true",
        help="CDL만 생성하고 Virtuoso에는 연결하지 않음",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="쉼표로 구분된 셀 이름 필터 (예: INV,NAND2,NOR2)",
    )
    parser.add_argument(
        "--pitch",
        type=float,
        default=0.30,
        help="layout transistor y-pitch (µm)",
    )
    args = parser.parse_args()

    specs = all_specs()

    if args.only:
        wanted = {name.strip().upper() for name in args.only.split(",") if name.strip()}
        specs = [spec for spec in specs if spec.name in wanted]
        if not specs:
            raise SystemExit(f"No matching cells: {sorted(wanted)}")

    write_cdl(specs, Path(args.out))

    if args.no_layout:
        print("[INFO] --no-layout: skipping Virtuoso layout generation.")
        return

    make_layouts(specs, args.lib, args.pitch)


if __name__ == "__main__":
    main()
