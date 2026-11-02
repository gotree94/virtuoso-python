"""GPDK045 / IC6.1.8 교육용 셀 정의 및 CDL 생성기.

이 모듈은 Virtuoso에 직접 의존하지 않습니다. 순수 Python으로 CDL만 생성하므로
Windows에서도 `python run.py --no-layout`으로 실행할 수 있습니다.

CDL 소자 순서: M<name> <drain> <gate> <source> <bulk> <model> w=.. l=.. nf=.. m=..
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# ---------------------------------------------------------------------------
# GPDK045 기본값
# ---------------------------------------------------------------------------
PDK = "gpdk045"          # 설치 폴더는 gpdk045_v_6_0, 라이브러리 이름은 gpdk045
LIB = "EDU45"            # 사용자가 만드는 작업 라이브러리

L = 0.045                # µm, GPDK045 기본 L
WN = 0.120               # µm, inverter NMOS 단위 폭
WP = 0.240               # µm, inverter PMOS 단위 폭 (이동도 보상)

NMOS_MODEL = "g45n1svt"  # PDK auCdl 설정에 따라 "nmos1v"일 수 있음
PMOS_MODEL = "g45p1svt"  # PDK auCdl 설정에 따라 "pmos1v"일 수 있음

Kind = Literal["inv", "nand", "nor", "mux2", "mux4"]


@dataclass(frozen=True)
class Spec:
    """셀 하나를 정의하는 최소 단위."""

    name: str
    kind: Kind
    n: int
    wn: float
    wp: float
    l: float = L
    nmos_model: str = NMOS_MODEL
    pmos_model: str = PMOS_MODEL

    @property
    def has_layout(self) -> bool:
        """EDU45.il이 현재 layout을 생성할 수 있는 종류인지 여부."""
        return self.kind in ("inv", "nand", "nor")


# ---------------------------------------------------------------------------
# 셀 팩토리
# ---------------------------------------------------------------------------
def inv() -> Spec:
    return Spec("INV", "inv", 1, WN, WP)


def nand(n: int) -> Spec:
    if not 2 <= n <= 10:
        raise ValueError(f"NAND 입력 수는 2~10이어야 합니다: {n}")
    # NMOS는 n개 직렬 -> 각 폭을 n배로 키워 구동력 보상
    return Spec(f"NAND{n}", "nand", n, WN * n, WP)


def nor(n: int) -> Spec:
    if not 2 <= n <= 10:
        raise ValueError(f"NOR 입력 수는 2~10이어야 합니다: {n}")
    # PMOS는 n개 직렬 -> 각 폭을 n배로 키워 구동력 보상
    return Spec(f"NOR{n}", "nor", n, WN, WP * n)


def mux2() -> Spec:
    return Spec("MUX2", "mux2", 2, WN, WP)


def mux4() -> Spec:
    return Spec("MUX4", "mux4", 4, WN, WP)


def all_specs() -> list[Spec]:
    specs: list[Spec] = [inv()]
    specs += [nand(n) for n in range(2, 11)]
    specs += [nor(n) for n in range(2, 11)]
    specs += [mux2(), mux4()]
    return specs


# ---------------------------------------------------------------------------
# CDL 생성
# ---------------------------------------------------------------------------
def _um(value: float) -> str:
    """0.045 -> '0.045u' 형태로 포맷."""
    return f"{value:g}u"


def _mos(
    name: str,
    drain: str,
    gate: str,
    source: str,
    bulk: str,
    model: str,
    w: float,
    l: float,
    nf: int = 1,
    m: int = 1,
) -> str:
    return (
        f"{name} {drain} {gate} {source} {bulk} {model} "
        f"w={_um(w)} l={_um(l)} nf={nf} m={m}"
    )


def cdl(spec: Spec) -> str:
    """Spec 하나를 CDL 문자열로 변환한다."""
    s = spec

    if s.kind == "inv":
        body = [
            _mos("MN0", "Y", "A", "VSS", "VSS", s.nmos_model, s.wn, s.l),
            _mos("MP0", "Y", "A", "VDD", "VDD", s.pmos_model, s.wp, s.l),
        ]
        pins = "A"
        return _wrap(s.name, pins, body)

    if s.kind == "nand":
        # NMOS series: VSS -> N1 -> ... -> N(n-1) -> Y
        nets = ["VSS"] + [f"N{i}" for i in range(1, s.n)] + ["Y"]
        body = [
            _mos(
                f"MN{i}",
                nets[i + 1],
                f"A{i}",
                nets[i],
                "VSS",
                s.nmos_model,
                s.wn,
                s.l,
            )
            for i in range(s.n)
        ]
        # PMOS parallel: VDD -> Y
        body += [
            _mos(
                f"MP{i}",
                "Y",
                f"A{i}",
                "VDD",
                "VDD",
                s.pmos_model,
                s.wp,
                s.l,
            )
            for i in range(s.n)
        ]
        pins = " ".join(f"A{i}" for i in range(s.n))
        return _wrap(s.name, pins, body)

    if s.kind == "nor":
        # NMOS parallel: VSS -> Y
        body = [
            _mos(
                f"MN{i}",
                "Y",
                f"A{i}",
                "VSS",
                "VSS",
                s.nmos_model,
                s.wn,
                s.l,
            )
            for i in range(s.n)
        ]
        # PMOS series: VDD -> P1 -> ... -> P(n-1) -> Y
        nets = ["VDD"] + [f"P{i}" for i in range(1, s.n)] + ["Y"]
        body += [
            _mos(
                f"MP{i}",
                nets[i + 1],
                f"A{i}",
                nets[i],
                "VDD",
                s.pmos_model,
                s.wp,
                s.l,
            )
            for i in range(s.n)
        ]
        pins = " ".join(f"A{i}" for i in range(s.n))
        return _wrap(s.name, pins, body)

    if s.kind == "mux2":
        # 2:1 transmission-gate MUX
        # A0 path: NMOS gate = S, PMOS gate = SN
        # A1 path: NMOS gate = SN, PMOS gate = S
        body = [
            _mos("MN0", "Y", "S", "A0", "VSS", s.nmos_model, s.wn, s.l),
            _mos("MP0", "Y", "SN", "A0", "VDD", s.pmos_model, s.wp, s.l),
            _mos("MN1", "Y", "SN", "A1", "VSS", s.nmos_model, s.wn, s.l),
            _mos("MP1", "Y", "S", "A1", "VDD", s.pmos_model, s.wp, s.l),
            # select inverter: S -> SN
            _mos("MN2", "SN", "S", "VSS", "VSS", s.nmos_model, s.wn, s.l),
            _mos("MP2", "SN", "S", "VDD", "VDD", s.pmos_model, s.wp, s.l),
        ]
        return _wrap(s.name, "A0 A1 S", body)

    if s.kind == "mux4":
        # 4:1 tree: 3 x MUX2
        # MUX2 포트 순서: A0 A1 S Y VDD VSS
        body = [
            "X0 A0 A1 S0 Y0 VDD VSS MUX2",
            "X1 A2 A3 S0 Y1 VDD VSS MUX2",
            "X2 Y0 Y1 S1 Y VDD VSS MUX2",
        ]
        return _wrap(s.name, "A0 A1 A2 A3 S0 S1", body)

    raise ValueError(f"지원하지 않는 kind: {s.kind}")


def _wrap(name: str, input_pins: str, body: list[str]) -> str:
    return (
        f".SUBCKT {name} {input_pins} Y VDD VSS\n"
        + "\n".join(body)
        + "\n.ENDS\n"
    )


if __name__ == "__main__":
    # 간단한 자체 점검: NAND2 CDL을 표준 출력으로 확인
    print(cdl(nand(2)))
