# myModules "Proposal FINAL" 제출본과 2026-08-04 수정본 비교

확인일: 2026-10-13

myModules의 `CSET M&D 25-29 Turnitin > Research Proposal > Proposal FINAL`에 등록된 파일은 2026-06-20에 올린 `Final_Proposal.docx`다. 2026-08-04에 Prof. E. Mnkandla께 이메일로 보낸 수정본 `Proposal Final_080426_1705.docx`(심사위원 지적 반영)와는 다른 파일이며, 이 수정본은 myModules에 올라가 있지 않다.

## 두 파일

| 구분 | myModules Proposal FINAL | 지도교수께 보낸 수정본 |
|---|---|---|
| 파일명 | `Final_Proposal.docx` | `Proposal Final_080426_1705.docx` |
| 날짜 | 2026-06-20 18:08 SAST 업로드 (myModules 표시) | 2026-08-04 17:32 KST 이메일 발송, 2026-10-10 재첨부 |
| 크기 | 85,947 bytes | 170,537 bytes |
| SHA-256 | `56e2f5a8844d0cbecf5e0c8c5fd534f9d3ba7e0eb73dad325b2265e1585a9a32` | `abb0e81c2f73b03e0555ed7fb7c73a95a16aa22b3b4b0d60190bb4a319029aaa` |
| 문서 속성의 마지막 수정 | 2026-06-20T16:06:26Z | 2026-08-04T08:05:00Z |
| Word 메모 | 없음 | 20개 (심사 지적별 수정 위치) |
| Turnitin | 유사도 7%, 채점 상태 Not marked | 제출 안 됨 |
| 저장소 안의 같은 파일 | 없음 | [`translations/Proposal Final_080426_1705.docx`](../../translations/Proposal%20Final_080426_1705.docx) |

myModules 파일은 저장소에 없고, Downloads 폴더의 `Final_Proposal.docx`와 `Final_Proposal_Taehong Kwon.docx`가 해시까지 같다.

수정본이 오간 메일:

- 2026-08-04 "Re: Final Dissertation Proposal Submitted to CSET M&D Turnitin — Attached for Your Review" (수정본, `Correction-Table_Taehong-Kwon_080426_1700.docx`)
- 2026-10-10 "Revised proposal of 4 August 2026 – request to complete the approval process (28576810)" (`CGS2_details_Taehong_Kwon.pdf`, 수정본, 수정표)

## 내용 차이

| 항목 | 2026-06-20 (myModules) | 2026-08-04 (수정본) |
|---|---|---|
| 표지 날짜 | June 2026 | August 2026 |
| 분량 | 9,933단어, 523문단 | 11,702단어, 544문단 |
| 주 연구 질문 | 63단어 | 28단어 |
| "Passport" 언급 (Human Passport 포함) | 0 | 24 |
| "Gitcoin" 언급 | 0 | 2 |
| "attestation" 언급 | 0 | 12 |
| "Sybil" 언급 | 4 | 20 |
| 3.4절 "Attestation-Based Reputation Tooling in Deployed DeFi Systems" | 없음 | 있음 |

문단 523개 중 414개(약 79%)는 같고 45곳이 바뀌었다. 바뀐 곳은 2026-08-02 심사위원 지적에 대한 수정이다. 지적 내용은 실제 DeFi 평판 도구(Gitcoin Passport 등)에 대한 논의가 없다는 것과 연구 질문이 장황하다는 것이었다. 6월 판은 지도교수진의 Word 코멘트 36개까지만 반영했다.

주 연구 질문, 2026-06-20 판 (63단어):

> In the setting of Arbitrum One-based GMX V2 perpetual swap position trading, from the perspective of DeFi protocols, risk analysts, wallet users, and researchers who need explainable wallet-level risk indicators, can EndorseRank—a Weighted PageRank metric built from ERC-20 approval/permit-derived allowance relationships—match or outperform Adaptive Weighted PageRank and transfer-based PageRank baselines, as measured by rank divergence, trading-success alignment, runtime, memory use, and convergence stability?

주 연구 질문, 2026-08-04 판 (28단어):

> Can EndorseRank, a Weighted PageRank computed over ERC-20 allowance relationships, match or outperform transaction-based PageRank baselines in ranking Arbitrum One wallets by trading success, at lower computational cost?

## myModules 슬롯 상태 (2026-10-13)

| 과제 | 제출 파일 | 제출 시각 (SAST) | Turnitin | 제출 횟수 |
|---|---|---|---|---|
| Proposal FINAL | `Final_Proposal.docx` | 2026-06-20 18:08 | 7% | 1/1 |
| Proposal REVISION | `Proposal-Revision_Taehong Kwon_28576810_04272026_1831.docx` | 2026-04-27 12:08 | 3% | 1/1 |
| Proposal DRAFT | `Proposal-Draft_Taehong Kwon_28576810.docx` | 2026-04-27 12:06 | 4% | 1/1 |

세 과제 모두 "Submitted for grading", "Not marked" 상태이고 추가 제출은 허용되지 않는다. FINAL 화면에는 수정·삭제 버튼이 없고, 수정 화면(`action=editsubmission`)은 `error/nopermission`을 돌려준다.

## 사실과 다른 기존 서술

다음 세 서술은 수정본이 FINAL 슬롯에 올라갔다고 적거나 그렇게 읽힌다. myModules에는 6월 파일만 있다.

- 2026-08-04 메일: "I will also re-submit the revised proposal file to the Turnitin module." 슬롯이 잠겨 있어 실행되지 않았다.
- 2026-10-10 메일: "I also uploaded the revised proposal to the Proposal FINAL slot on the CSET M&D Turnitin."
- 윤리 신청서(ERM 2026-18316-29462) 지연 사유: "…submitted to the supervisor on 4 August 2026 and uploaded to the CSET M&D Turnitin Proposal FINAL slot."

## 할 일

- [ ] 지도교수께 Proposal FINAL의 추가 제출 기회(additional attempt)를 요청한다. "revert to draft"는 6월 제출 기록을 지우므로 요청하지 않는다.
- [ ] 슬롯이 열리면 Word 메모를 지운 수정본 사본을 올린다.
- [ ] 위 세 서술을 지도교수와 윤리위원회에 정정한다.

## 확인 방법

- myModules 파일: 로그인한 브라우저에서 제출 파일을 받아 SHA-256을 계산했다(디스크에 저장하지 않음).
- 로컬 파일: `sha256sum`.
- 내용: 두 docx의 `word/document.xml`에서 문단 텍스트를 뽑아 Python `difflib.SequenceMatcher`로 비교했다. 단어 수와 언급 횟수는 문단 텍스트 기준이다.
