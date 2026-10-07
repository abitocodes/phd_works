# Stacks 패키지 레지스트리를 위한 Clarity 스마트 컨트랙트 순위 산정: ERC-20 allowance를 대신하는 포스트컨디션

영문 제목(폴더 이름의 근거): *Ranking Clarity Smart Contracts for a Package Registry on Stacks: Post-Conditions in Place of ERC-20 Allowances*

Stacks 블록체인에 배포된 Clarity 스마트 컨트랙트를 npmjs.com이나 pkg.go.dev처럼 찾고 쓰는 서비스(웹: Clarity Registry, CLI: `cpm`)와, 그 검색 순위를 시빌 공격에 버티도록 매기는 방법(PC-EndorseRank)에 관한 논문 작업 폴더입니다. 폴더 이름은 영문 제목을 줄인 것입니다(ERC-20 논문 폴더와 같은 규칙: 신호-방법-대상-용도).

ERC-20 논문(`../ERC20-Allowance-PageRank-Wallet-Reputation/`)의 EndorseRank와 AWP를 Stacks로 옮기되, Stacks에는 allowance가 없으므로 포스트컨디션과 Clarity 코드의 참조로 바꿉니다. 왜 그렇게 바꾸는지는 [`docs/allowance-replacement.ko.md`](docs/allowance-replacement.ko.md)에 정리했습니다.

## 상태

- **원고 초안**(한국어, 2026-10-07): 문제, 배경, 관련 연구, allowance 대응, 방법과 명제 3개, 레지스트리와 `cpm` 설계, 평가 설계, 한계까지 썼습니다. 처음에 쓴 영문판은 커밋 `7147a29`에 남아 있습니다.
- **실데이터 결과는 아직 없습니다.** 7절은 결과를 보기 전에 고정하는 평가 계획입니다(동결 T0 = 2026-10-31, 라벨 기간 2026-11-01 ~ 2027-01-31). 날짜와 매개변수를 담은 설정 파일을 11월 1일 전에 커밋해야 사전 등록이 됩니다.
- 5.7절과 부록 B의 표는 **합성 그래프**에서 나온 예시입니다. Stacks 메인넷 결과가 아닙니다.
- 대상 학술지, 공저자, 연락처는 정하지 않았습니다(`manuscript/Sections/00-title-abstract.tex`의 주석).

## 폴더

| 경로 | 내용 |
|------|------|
| `manuscript/` | 한국어 원고 LaTeX(XeLaTeX, kotex). `main.tex`가 `Sections/`의 절을 묶습니다. 빌드한 `main.pdf`도 함께 둡니다. |
| `manuscript/Sections/` | 00 제목·초록, 01 서론, 02 배경, 03 관련 연구, 04 allowance → Stacks 대응, 05 PC-EndorseRank, 06 레지스트리와 `cpm`, 07 평가 설계, 08 논의와 한계, 09 결론, 10 참고문헌(원어 그대로), 11 부록 |
| `manuscript/tables/` | `scripts/toy_sybil_example.py --latex`가 만든 표와 숫자 매크로. **손으로 고치지 않습니다.** |
| `scripts/toy_sybil_example.py` | 합성 그래프에서 세 가지 공격(가짜 컨트랙트, 가짜 지갑, 라우터 trait 인자 끼워 넣기)의 비용을 다섯 가지 점수 규칙으로 비교하는 스크립트(numpy만 필요, 시드 고정) |
| `docs/allowance-replacement.ko.md` | "allowance를 무엇으로 대체하나"에 대한 설계 메모 |

## 빌드

```powershell
cd manuscript
.\build.ps1
```

다른 환경에서는 `xelatex main.tex`를 두 번 실행하면 됩니다. 한글은 kotex로 조판하며, 쉬운 한국어 번역본(`../ERC20-Allowance-PageRank-Wallet-Reputation/dissertation/overleaf-github-ko/`)과 같은 글꼴 설정을 씁니다. 로마자는 Times New Roman(없으면 같은 글자 폭의 Liberation Serif), 한글은 Windows에서 바탕·맑은 고딕, Linux에서 나눔명조·나눔고딕·나눔고딕코딩을 씁니다.

합성 예제 표를 다시 만들 때:

```powershell
python scripts/toy_sybil_example.py --latex
```

## 규칙

- 원고 본문, README, 메모, 스크립트의 설명과 출력은 한국어로 씁니다. 폴더 이름과 파일 이름은 영어로 둡니다. 참고문헌 목록은 찾아보기 쉽도록 원어 그대로 둡니다.
- `manuscript/tables/`의 숫자는 스크립트로만 바꿉니다. 실데이터 결과가 생기면 같은 방식(스크립트 → 표 조각 → `\input`)으로 넣습니다.
- 문체는 ERC-20 논문의 규칙을 따릅니다(`../../HANDOFF.md`의 "Dissertation prose must not read as AI-written"). 부풀린 말, 틀에 박힌 세 항목 나열, 요약으로 끝맺는 문장을 쓰지 않고, 문장을 짧고 구체적으로 씁니다.

## 다음 단계

1. 직접 운영하는 Stacks 노드와 Stacks Blockchain API로 메인넷 데이터 파이프라인을 만듭니다(이 작업 환경에서는 Hiro 호스팅 API가 네트워크 정책으로 막혀 있었습니다).
2. 7절의 날짜, 매개변수, 시드, 결정 규칙을 설정 파일로 옮겨 11월 1일 전에 커밋합니다.
3. RQ1(포스트컨디션 사용 실태)부터 기술 통계를 냅니다. Allow 모드 비율이 높으면 4절의 규칙을 다시 봅니다.
4. Clarity 파서와 정규화 해시, `cpm add`/`cpm verify` 시제품을 만듭니다.
