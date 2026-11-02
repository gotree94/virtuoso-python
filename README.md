# Virtuoso + Python 자동 생성 스캐폴드 (GPDK045 / IC6.1.8)

Cadence Virtuoso에서 인버터, 2~10입력 NAND/NOR, 2:1/4:1 MUX를 **풀커스텀으로 그리지 않고** Python 스크립트로 생성하기 위한 교육용 스캐폴드입니다.

핵심 구조는 다음과 같습니다.

```text
Python (cells.py)
  ├─ CDL 생성  ──> Virtuoso CDL In ──> schematic
  └─ skillbridge ──> SKILL EDU_make_layout() ──> layout
                          │
                          ├─ PVS / Assura DRC·LVS
                          ├─ QRC PEX
                          └─ Spectre PVT / transient
```

중요: Virtuoso를 Python으로 완전히 대체하는 것이 아닙니다. **Virtuoso의 customization 언어는 SKILL**이고, Python은 SKILL API를 호출하는 오케스트레이터 역할을 합니다. Cadence 포럼(2025)에서도 "Virtuoso를 커스터마이즈하는 일반 Python 인터페이스는 없고, 언어는 SKILL"이라고 답변하고 있습니다.

---

## 1. 전제 환경

| 항목 | 값 |
|---|---|
| PDK | GPDK045 v6.0 (`gpdk045_v_6_0`) |
| Virtuoso | IC6.1.8 (IC618) |
| Python | 3.8 이상 |
| 브리지 | `skillbridge` 1.8.x |
| 실행 위치 | Virtuoso와 **같은 Linux 호스트** (skillbridge는 POSIX 기반) |

GPDK045 v6.0 릴리스 노트에는 `gpdk045 IC618 library is built natively with IC6.1.8 ISR4`라고 명시되어 있습니다. IC618과 정확히 맞는 버전이므로 버전 불일치 문제는 거의 없습니다.

> Windows에서 작업하는 경우: Python은 Windows에서 CDL만 생성하고, layout 생성은 SSH로 Linux 호스트에 접속해서 실행하는 구성을 권장합니다. `skillbridge`는 Windows 로컬에서 Virtuoso에 직접 붙는 용도로 설계되지 않았습니다.

---

## 2. 폴더 구조

```text
virtuoso-python/
├─ README.md          # 이 문서
├─ cells.py           # 셀 정의 + CDL 생성기
├─ run.py             # CDL 생성 + skillbridge layout 호출
├─ verify.py          # DRC/LVS/Spectre 실행 스켈레톤
├─ EDU45.il           # GPDK045 layout 생성 SKILL 코드
├─ requirements.txt   # Python 의존성
└─ cdl/               # run.py가 생성하는 CDL 파일 (자동 생성)
```

---

## 3. GPDK045 실제 이름 (스크립트에 넣을 값)

인터넷 예제에서 많이 틀리는 부분입니다. GPDK045는 `M1`, `OD`가 아니라 아래 이름을 사용합니다.

| 항목 | 실제 값 |
|---|---|
| PDK 라이브러리 | `gpdk045` (설치 폴더는 `gpdk045_v_6_0`) |
| 코어 소자 | `nmos1v`, `pmos1v` |
| 기타 소자 | `nmos1v_hvt/lvt`, `pmos1v_hvt/lvt`, `nmos2v`, `pmos2v` |
| 기본 W/L | **120n / 45n** (nmos1v, pmos1v 둘 다) |
| Spectre 모델 | `g45n1svt`, `g45p1svt` |
| CDL 소자명 | `g45n1svt`, `g45p1svt` (PDK `auCdl` 설정에 따라 `nmos1v`/`pmos1v`) |
| 레이어 | `Oxide`, `Poly`, `Nimp`, `Pimp`, `Nwell`, `Cont`, `Metal1`, `Metal2`, `Via1` |
| Via 정의 | `M1_PO`, `M1_NWELL`, `M1_PSUB`, `M2_M1` |
| DRC/LVS (Assura) | `assuraDRC.rul`, `extract.rul`, `compare.rul` |
| DRC/LVS (PVS) | `pvlDRC.rul`, `pvlLVS.rul` |
| 기생추출 | `qrc/` |

**주의**

- `Metal1`을 `M1`로 쓰면 `dbCreateRect`에서 레이어를 찾지 못합니다.
- `Oxide`를 `OD`로 쓰면 마찬가지로 실패합니다.
- 소자의 실제 pcell 파라미터명은 인스턴스를 선택한 뒤 `q`(Edit Properties)로 확인하세요. 일반적으로 `w`, `l`, `nf`, `m`을 사용합니다.

---

## 4. 셀 목록과 사이징

`cells.py`는 다음 셀을 생성합니다.

| 종류 | 셀 이름 | 비고 |
|---|---|---|
| Inverter | `INV` | 1 NMOS + 1 PMOS |
| NAND | `NAND2` ~ `NAND10` | NMOS 직렬 n단, PMOS 병렬 n개 |
| NOR | `NOR2` ~ `NOR10` | NMOS 병렬 n개, PMOS 직렬 n단 |
| MUX | `MUX2`, `MUX4` | 2:1 transmission gate, 4:1 tree |

기본 사이징은 `L=45n`, `Wn=120n`, `Wp=240n`입니다.

| n | NAND Wn(each) | NAND NMOS 총폭 | NOR Wp(each) | NOR PMOS 총폭 |
|---|---|---|---|---|
| 2 | 0.24 µm | 0.48 µm | 0.48 µm | 0.96 µm |
| 4 | 0.48 µm | 1.92 µm | 0.96 µm | 3.84 µm |
| 6 | 0.72 µm | 4.32 µm | 1.44 µm | 8.64 µm |
| 8 | 0.96 µm | 7.68 µm | 1.92 µm | 15.36 µm |
| 10 | 1.20 µm | **12.0 µm** | 2.40 µm | **24.0 µm** |

규칙:

- **NAND-n**: NMOS n개 직렬이므로 각 NMOS 폭을 `Wn × n`으로 키우고, PMOS는 병렬이므로 `Wp`를 유지합니다.
- **NOR-n**: PMOS n개 직렬이므로 각 PMOS 폭을 `Wp × n`으로 키우고, NMOS는 병렬이므로 `Wn`을 유지합니다.
- 실제 구동력은 Spectre 시뮬레이션으로 재조정해야 합니다. 위 값은 "동일 구동력"을 위한 출발점입니다.

---

## 5. 교육용 현실적 범위

| 항목 | 자동화 수준 | 비고 |
|---|---|---|
| INV, NAND2~10, NOR2~10 schematic | 전부 | CDL 생성 후 CDL In |
| INV, NAND2~4, NOR2~4 layout | 전부 | `EDU45.il` 템플릿 |
| NAND5~10, NOR5~10 layout | 선택 | folding/DRC 반복 필요 |
| MUX2, MUX4 schematic | 전부 | CDL 생성 |
| MUX2, MUX4 layout | 스텁 | 템플릿 직접 작성 필요 |
| 10입력 layout | 비추천 | NAND10 NMOS 12 µm, NOR10 PMOS 24 µm |

"2~10입력 전부"를 만들면 셀은 18개지만, **레이아웃이 병목**입니다. 4주 과제라면 schematic 전체 + layout은 4입력까지가 적당합니다.

---

## 6. 아키텍처

### 6.0 선택지 비교

| 방식 | 장점 | 단점 | 이 프로젝트 |
|---|---|---|---|
| Python + skillbridge → SKILL API | Python으로 전부 제어, Jupyter/디버깅 편함 | SKILL API 학습 필요, 버전 의존 | layout 생성에 사용 |
| SKILL PCell + Python 오케스트레이션 | DRC-safe, 재사용성 높음, 실무 표준 | PCell 코드는 SKILL | `EDU45.il` |
| gdsfactory/KLayout → GDS import | 무료·강력·버전 독립 | PDK layer/DRC 매핑, 핀/계층 손실 | 사용하지 않음 |
| Python → CDL → CDL In | schematic 자동화가 매우 안정적 | layout은 별도 | schematic 생성에 사용 |

결론: **schematic은 CDL, layout은 SKILL**이 교육용에서 가장 안정적입니다.

### 6.1 Schematic

SKILL schematic API로 직접 배선하는 것보다 **CDL을 생성해서 CDL In으로 가져오는 방식**이 훨씬 안정적입니다.

`cells.py`가 만드는 CDL 예시 (`NAND2`):

```spice
.SUBCKT NAND2 A0 A1 Y VDD VSS
MN0 N1 A0 VSS VSS g45n1svt w=0.24u l=0.045u nf=1
MN1 Y A1 N1 VSS g45n1svt w=0.24u l=0.045u nf=1
MP0 Y A0 VDD VDD g45p1svt w=0.24u l=0.045u nf=1
MP1 Y A1 VDD VDD g45p1svt w=0.24u l=0.045u nf=1
.ENDS
```

### 6.2 Layout

`EDU45.il`의 `EDU_make_layout()`이 GPDK045 pcell을 `dbCreateParamInstByMasterName()`으로 배치합니다.

```lisp
dbCreateParamInstByMasterName(
  cv "gpdk045" "nmos1v" "layout" "MN0" list(0.0 0.0) "R0" 1
  list(list("w" "float" 0.24) list("l" "float" 0.045)
       list("nf" "int" 1) list("m" "int" 1)))
```

이 스캐폴드는 **배치 골격**입니다. DRC/LVS를 통과하려면 다음이 추가로 필요합니다.

- Metal1/Metal2 배선
- `Cont`, `Via1`, `M1_PO`, `M1_NWELL`, `M1_PSUB`
- `Nwell`, `Nimp`, `Pimp`, `Poly`, `Oxide`
- body tie / tap
- pin shape + label
- dummy / density fill

이 배선 부분이 전체 작업의 약 70%입니다.

---

## 7. 설치 및 준비

### 7.1 Python 패키지

Linux 호스트에서:

```bash
python3 -m pip install -r requirements.txt
```

### 7.2 skillbridge 서버

```bash
skillbridge path
```

출력된 경로를 Virtuoso CIW에서 load합니다.

```lisp
load("/path/to/skillbridge.il")
pyStartServer
```

### 7.3 SKILL 코드 로드

Virtuoso CIW에서:

```lisp
load("/path/to/EDU45.il")
```

`EDU45.il`은 `EDU_make_layout()` 함수를 정의합니다. Python에서 `ws.EDU_make_layout(...)`로 호출합니다.

### 7.4 라이브러리 준비

Library Manager에서 `EDU45` 라이브러리를 만들고 technology를 `gpdk045`에 attach합니다.

```text
Library Manager > File > New > Library
Name: EDU45
Attach to existing tech library: gpdk045
```

---

## 8. 사용법

### 8.1 CDL만 생성 (Virtuoso 없이 가능)

Windows 또는 Linux 어디서나:

```bash
python run.py --no-layout
```

`cdl/` 폴더에 `INV.cdl`, `NAND2.cdl` ... `NOR10.cdl`, `MUX2.cdl`, `MUX4.cdl`이 생성됩니다.

### 8.2 Virtuoso layout까지 생성

Virtuoso와 같은 Linux 호스트에서:

```bash
python run.py
```

`run.py`는 다음 순서로 동작합니다.

1. 모든 셀의 CDL을 `cdl/`에 저장
2. `skillbridge`로 Virtuoso에 연결
3. `INV`, `NAND2~10`, `NOR2~10`에 대해 `EDU_make_layout()` 호출
4. MUX는 layout 템플릿이 아직 없으므로 건너뜀

### 8.3 Schematic 만들기 (CDL In)

Virtuoso에서:

```text
File > Import > CDL
Input File: cdl/NAND2.cdl
Target Library: EDU45
```

CDL In에서 소자 매핑이 실패하면 모델명을 `g45n1svt`에서 `nmos1v`로, `g45p1svt`에서 `pmos1v`로 바꿔보세요. PDK의 `auCdl` view 설정에 따라 요구하는 이름이 다릅니다.

`MUX4.cdl`은 `MUX2`를 subcircuit으로 참조합니다. `MUX4`를 import하기 전에 같은 라이브러리에 `MUX2` schematic이 먼저 있어야 합니다.

### 8.4 생성 결과 확인

```text
Library Manager > EDU45 > NAND2 > layout
```

`EDU45.il`은 배치만 수행하므로, 배선/pin은 아직 없습니다. DRC/LVS는 배선을 추가한 뒤 실행하세요.

---

## 9. 레이아웃 코드 설명

### 9.1 `EDU_mos`

GPDK045 pcell 인스턴스를 생성하는 공통 함수입니다.

```lisp
procedure(EDU_mos(cv master name x y w l nf m)
  let((params)
    params = list(
      list("w"  "float" w)
      list("l"  "float" l)
      list("nf" "int"   nf)
      list("m"  "int"   m))
    dbCreateParamInstByMasterName(
      cv "gpdk045" master "layout" name list(x y) "R0" 1 params)
  )
)
```

- `w`, `l` 단위는 µm입니다.
- `nf`는 finger 수입니다. 폭이 큰 소자는 `nf`로 접어서 배치할 수 있습니다.
- `m`은 multiplier입니다.
- pcell 파라미터명이 다르면 `q`로 확인 후 수정하세요.

### 9.2 `EDU_nand_lay`

- NMOS를 y축으로 `pitch` 간격으로 직렬 배치
- PMOS를 x=0.9µm 위치에 병렬 배치
- 상하단에 Metal1 rail 생성

### 9.3 `EDU_nor_lay`

- NMOS를 병렬 배치
- PMOS를 y축으로 직렬 배치
- 상하단에 Metal1 rail 생성

### 9.4 `EDU_make_layout`

`kind` 값에 따라 `EDU_inv_lay` / `EDU_nand_lay` / `EDU_nor_lay`를 호출합니다. `mux2`/`mux4`는 현재 스텁(`EDU_mux2_lay`)만 있으므로 `run.py`에서 layout 생성을 건너뜁니다.

### 9.5 확장: Euler trail 기반 배치

현재 `EDU45.il`은 단순 행/열 배치입니다. NAND/NOR처럼 series-parallel graph인 셀은 다음 순서로 확장할 수 있습니다.

1. transistor network graph 생성 (직렬/병렬)
2. Euler trail 탐색 → diffusion 공유가 최대인 stick diagram
3. 폭이 큰 소자는 `nf`로 folding
4. diffusion break 최소화 배치
5. Metal1 local route + Metal2 vertical route
6. well/tap/implant/dummy 삽입 → DRC loop

10입력처럼 trail이 길어지면 setback과 높이가 급격히 커지므로, 5입력 이상은 트리 분할이 더 현실적입니다.

---

## 10. 검증

### 10.1 DRC

PVS 예시:

```bash
strmout -library EDU45 -strmFile EDU45.gds -topCell NAND2 -view layout
pvs -drc pvlDRC.rul -gds EDU45.gds -top NAND2 ...
```

Assura 예시:

```bash
strmout -library EDU45 -strmFile EDU45.gds -topCell NAND2 -view layout
assura assuraDRC.rul ...
```

정확한 CLI 인자는 PDK 설치 경로의 runset과 사이트 환경에 따라 다릅니다. `verify.py`는 이 부분을 템플릿으로 감싸둔 스켈레톤입니다.

### 10.2 LVS

- PVS: `pvlLVS.rul`
- Assura: `extract.rul` + `compare.rul`

LVS를 통과하려면 layout에 pin/label이 있어야 합니다. `EDU45.il`의 pin 생성 부분은 TODO로 남겨두었습니다.

### 10.3 PEX

`qrc/` 디렉토리의 runset을 사용합니다.

### 10.4 Spectre

GPDK045 모델은 `gpdk045.scs`에 있으며, 일반적으로 `tt`, `ff`, `ss`, `fs`, `sf`, `mc` 코너를 제공합니다.

```text
Model Library: gpdk045.scs
Section: tt
```

`verify.py --mode sim`은 Spectre 실행과 로그 파싱을 위한 골격입니다.

---

## 11. 10입력 주의

NAND10은 NMOS 10개가 직렬이므로 각 NMOS 폭이 `1.2 µm`, 총 NMOS 폭이 `12 µm`입니다. NOR10은 PMOS 10개가 직렬이므로 각 PMOS 폭이 `2.4 µm`, 총 PMOS 폭이 `24 µm`입니다.

교육적으로는 다음을 보여주기 좋습니다.

- 직렬 stack이 길어질수록 동일 구동력을 위해 폭이 선형으로 증가
- NOR가 NAND보다 불리한 이유 (PMOS 이동도)
- 10입력 단일 게이트가 비현실적인 이유
- 트리 분할 (NAND4 + NAND3 + INV 등) 또는 AOI/OAI 복합 게이트가 필요한 이유

실제 라이브러리에서는 4입력 이하를 기본으로 하고, 5입력 이상은 분할하는 구성을 권장합니다.

---

## 12. 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `dbCreateRect`에서 layer not found | `M1`, `OD` 사용 | `Metal1`, `Oxide`로 변경 |
| pcell 파라미터가 적용되지 않음 | 파라미터명/타입 불일치 | 인스턴스 선택 후 `q`로 확인, `"float"`/`"int"` 타입 맞추기 |
| `skillbridge` 연결 실패 | Python이 다른 호스트에서 실행 | Virtuoso와 같은 Linux 호스트에서 실행 |
| `pyStartServer` 없음 | skillbridge load 안 됨 | `load("/path/to/skillbridge.il")` 후 `pyStartServer` |
| CDL In에서 소자 인식 실패 | 모델명 불일치 | `g45n1svt` ↔ `nmos1v` 교체 |
| DRC가 네트워크 드라이브에서 실패 | PVS/Assura 임시파일 권한 | CIW를 로컬 디렉토리에서 실행 |
| LVS에서 pin 없음 | pin/label 미생성 | `dbCreatePin`/label 추가 |

---

## 13. 로드맵

| 단계 | 내용 | 예상 |
|---|---|---|
| Phase 0 | `EDU45` 라이브러리 생성, `gpdk045` attach, unit INV 수동 제작 | 1일 |
| Phase 1 | CDL 생성기로 INV/NAND2~10/NOR2~10 schematic 생성 | 1주 |
| Phase 2 | `EDU45.il`로 INV/NAND2/NOR2 layout 배치, DRC/LVS 통과 | 1~2주 |
| Phase 3 | NAND3~4/NOR3~4, MUX2/4 layout 템플릿 | 1~2주 |
| Phase 4 | Spectre PVT/transient 자동화, delay/power 리포트 | 1주 |
| Phase 5 | 10입력은 schematic+sim만, 분할 게이트와 비교 | 선택 |

---

## 14. 참고 문서

- GPDK045 v6.0 PDK Reference Manual
- GPDK045 v6.0 DRC/LVS 문서
- Cadence SKILL Reference (IC618)
- `skillbridge` 문서: <https://unihd-cag.github.io/skillbridge/>
- Cadence Community: "Does Cadence provide a standard Python API for tool automation?" (2025)

---

## 15. 라이선스 / 주의

이 스캐폴드는 교육용입니다. GPDK045는 Cadence 교육용 PDK이며, 실제 silicon sign-off용이 아닙니다. DRC/LVS/PEX 결과는 교육 목적으로만 사용하세요.
