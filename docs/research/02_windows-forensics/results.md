# 실험 결과

> 상태: **실험 설계 완료 / 실측 전**. 아래 4장 표의 '결과' 열은 실험 후 기입한다.
> 가상 데이터(samples/synthetic)는 엔진 검증용이므로 이 문서의 결과로 인용하지 않는다.

## 1. 실험 환경
| 항목 | 값 (실험 시 기입) |
|---|---|
| OS | Windows 11 23H2/24H2 (VM, 스냅샷 기반으로 실험마다 초기화) |
| 브라우저 | Chrome 최신, Edge 최신 |
| 도구 | Sysmon(collector/sysmon-shadowai.xml), EZ Tools(MFTECmd/LECmd/JLECmd/RECmd), FTK Imager 또는 KAPE |
| 시간 동기화 | VM 시간 NTP 동기화 확인, 각 동작 시각을 스톱워치/스크린 녹화로 별도 기록(기준 시각) |
| 테스트 파일 | `테스트_재무.xlsx`, `테스트_고객.csv`, `테스트.zip` (내용은 더미) |

## 2. 실험 목적
상관분석 엔진(01_detection)이 전제한 **파일 아티팩트 동작을 실측으로 검증**한다. 특히 SAI-004(업로드)·SAI-005(다운로드) 규칙의 근거가 실제로 남는지 확인한다.

## 3. 실험 과정
각 실험은 **스냅샷 복원 → Sysmon 로그 초기화 → 동작 수행(시각 기록) → 수집(collect_artifacts.ps1) → 엔진 분석** 순서로 진행하고, 동작별 3회 반복한다.

| ID | 동작 | 확인할 아티팩트 |
|---|---|---|
| W-1 | 탐색기에서 xlsx 더블클릭으로 열기 | Recent LNK 생성/수정시각, Excel JumpList, $SI 접근시각 갱신 여부 |
| W-2 | ChatGPT 웹에서 '파일 첨부' → 파일 선택창에서 csv 선택 → 전송 | **Recent LNK 생성 여부**, OpenSavePidlMRU(csv)·LastVisitedPidlMRU(chrome.exe), USN 변화 |
| W-3 | W-2 와 동일하되 파일 선택 후 '취소' | W-2 와 아티팩트 차이 (업로드 취소 구분 가능성) |
| W-4 | 파일을 Chrome 창으로 드래그&드롭 업로드 | 대화상자 없이 업로드 시 남는 흔적 (LNK 미생성 예상) |
| W-5 | ChatGPT 가 만든 파일 다운로드 | Chrome downloads(tab_url, referrer), Zone.Identifier HostUrl/ReferrerUrl, USN(.crdownload → Rename) |
| W-6 | Claude·Gemini 에서 W-2, W-5 반복 | 서비스별 업로드/다운로드 도메인 차이 |
| W-7 | 파일 복사(Ctrl+C/V) 후 복사본 업로드 | $SI 생성>수정 (Copied 플래그) 확인 |
| W-8 | 업로드한 파일 삭제 → 휴지통 비우기 | USN FileDelete, $I/$R, Sysmon EID 26 |

## 4. 실험 결과
| ID | 기대 | 결과 (반복 1/2/3) | 엔진 탐지 결과 | 비고 |
|---|---|---|---|---|
| W-1 | LNK·JumpList 갱신 | | | |
| W-2 | LNK 생성 + ComDlg32 기록 | | | SAI-004 전제 |
| W-3 | W-2 와 동일(구분 불가) 예상 | | | |
| W-4 | LNK 없음 | | | SAI-004 미탐 범위 |
| W-5 | tab_url·HostUrl 이 AI 도메인 | | | SAI-005 전제 |
| W-6 | | | | |
| W-7 | Copied=True | | | |
| W-8 | FileDelete 기록 | | | SAI-009 |

## 5. 확인된 한계
(실험 후 기입) — 예상 한계: 드래그&드롭 업로드(W-4)는 LNK 를 남기지 않을 가능성이 높아 텔레메트리(04) 없이는 탐지 어려움.

## 6. 추가 연구 사항
- RECmd ComDlg32 출력 파서를 엔진에 추가 (W-2 결과가 긍정적일 경우)
- Windows 10 vs 11, Chrome vs Edge 차이 비교
