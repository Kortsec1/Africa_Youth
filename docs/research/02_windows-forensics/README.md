# 연구 주제
* Windows 파일 시스템 포렌식

## 1. 연구 목표
* Windows 파일 작업 과정에서 발생하는 포렌식 아티팩트를 분석하고,
* AI 서비스 사용 전후의 파일 활동을 추적할 수 있는지 검증한다.

## 2. 기술 조사
# 1. 아티팩트 수집 및 파싱
* LNK(링크 파일)
- 생성 조건
  - 사용자가 바탕화면 등에서 직접 바로 가기를 만들었을 때.
  - 사용자가 로컬 또는 네트워크 드라이브의 문서나 파일을 열었을 때 시스템이 최근 문서 기록용으로 자동 생성함.
  - 위치: %USERPROFILE%\AppData\Roaming\Microsoft\Windows\Recent
  - 파싱: LECmd.exe를 사용하여 대상 파일의 원본 경로, MAC(수정/접근/생성) 타임, 볼륨 시리얼 넘버 등을 추출.

* JumpList
- 생성 조건
  - 사용자가 특정 응용프로그램을 통해 파일을 열거나 상호작용할 때, 해당 프로그램의 AppID와 연동되어 자동 생성·갱신.
  - 내부적으로 링크(.lnk) 파일 형식을 포함하여 최근 사용(MRU) 및 자주 사용(MFU) 기록을 남김.
  - 위치: %USERPROFILE%\AppData\Roaming\Microsoft\Windows\Recent\AutomaticDestinations
  - 파싱: JLECmd.exe를 사용하여 사용자가 응용 프로그램(예: Chrome, Word)을 통해 어떤 파일을 언제 열었는지 Application ID와 함께 분석.

* $MFT
  - 위치: NTFS 볼륨의 루트 디렉터리 (숨김 속성)
  - 추출/파싱: FTK Imager로 파일 추출 후, MFTECmd.exe를 사용하여 파싱. $UsnJrnl의 경우 $J 데이터 스트림을 추출하여 파싱.

# 2. 파일 행위 별 교차 검증 방법

* 분석 대상 행위
  - 아티팩트 교차 검증 시나리오 (어떻게 분석하는가?)
* 파일 생성
  - $MFT: 새로운 레코드가 할당되고 $SI와 $FN의 생성 시간이 동일하게 기록됨.
* 파일 단순 열기
  - LNK / JumpList: 사용자가 직접 파일을 클릭해 열었다면 Recent 폴더에 LNK가 생성/갱신되고, 해당 연결 프로그램의 JumpList에 기록이 추가됨.
  - $MFT: $SI의 접근 시간(Access Time)이 갱신될 수 있으나, Windows 버전에 따라 비활성화되어 있을 수 있어 LNK/JumpList 의존도가 높음.
* 파일 수정
  - $MFT: $SI의 수정 시간(Modified Time)이 갱신됨. ($FN 시간은 유지됨)
  - $UsnJrnl: DataOverwrite, DataExtend, FileClose 이벤트가 순차적으로 로깅됨. (실제 데이터 변경의 확실한 증거)
* 파일 복사
  - $MFT (목적지 파일): 복사된 위치에 새 레코드 할당. 생성 시간(Creation Time)은 현재 시간으로 기록되지만, 수정 시간(Modified Time)은 원본 파일의 시간을 그대로 가져옴 (이 차이가 복사의 핵심 증거).
* 파일 삭제
  - $MFT: 파일 레코드의 플래그가 Allocated에서 Unallocated로 변경됨.
  - $UsnJrnl: FileDelete 이벤트가 기록되며, 휴지통으로 이동한 경우 파일명이 $I... / $R... 형태로 변경되는 Rename 이벤트가 동반됨. 
# 3. AI 서비스 사용 전 후 활동 추적 적용
* AI 서비스 접속 인지: 웹 브라우저(Chrome 등)의 웹 히스토리(History 아티팩트) 또는 JumpList를 통해 AI 서비스에 언제 접속했는지 타임라인의 기준점을 잡음.

* 파일 접근/업로드 추적: AI 서비스에 로컬 파일을 업로드하기 위해 파일 탐색기 창을 열고 파일을 선택했다면, 대상 파일의 LNK 파일이 생성되거나 갱신될 확률이 높음.

* 파일 다운로드/저장 추적: AI가 생성한 결과물을 다운로드했다면, 브라우저 다운로드 경로에 새로운 $MFT 레코드가 생성되며, $UsnJrnl에 브라우저 프로세스에 의한 FileCreate 기록이 남음.

## 3. 프로젝트 적용 가능성

* 1. 민감한 내부 문서 업로드 (데이터 유출) 정황 추적
    - 분석 시나리오 : 네트워크 로그나 히스토리를 통해 특정 직원 PC에서 오후00시 00분에 ChatGPT 접속 기록을 확인하였으나 네트워크 패킷이 암호화 되어 있어 알 수 없음.
     - 아티팩트 적용 : JumpList & LNK로 해당 시간대(오후 00시 00분경)에 생성되거나 갱신된 LNK 파일과 JumpList를 확인합니다. 만약 이 시간에 2026_Q3_재무제표.xlsx 파일에 대한 LNK 타임스탬프가 갱신되었다면, 직원이 AI 프롬프트에 첨부하기 위해 파일 탐색기에서 해당 파일을 선택(접근)했을 확률이 매우 높음.
* 2. AI가 생성한 악성코드 또는 자동화 결과물 저장
  - $MFT & $UsnJrnl (Downloads 경로): 브라우저를 통해 AI가 생성한 결과물(예: 코드 텍스트 파일, 다운로드된 문서)이 저장될 때 생성되는 $MFT 레코드와 $UsnJrnl의 FileCreate 이력을 분석함.   
* 3. 비인가 AI 데스크톱 앱 및 스크립트 사용 식별
  - $MFT: %AppData%나 Program Files 경로에 비인가 AI 앱의 설치 흔적이나 캐시, SQLite DB 파일이 생성된 시간($SI, $FN 타임스탬프)을 분석하여 언제부터 사용했는지 특정함. 

## 3-1. 추가 조사: 업로드·다운로드를 보강하는 아티팩트
* Zone.Identifier (ADS, Mark of the Web)
  - 브라우저로 받은 파일에 `파일명:Zone.Identifier` 스트림이 생기고 `ZoneId=3`, `HostUrl`, `ReferrerUrl` 이 기록됨.
  - MFTECmd 는 `ZoneIdContents` 컬럼으로, Sysmon 은 EID 15(FileCreateStreamHash)의 `Contents` 필드로 출력.
  - AI 생성물 다운로드(SAI-005)의 '출처 URL' 증거. 단, 브라우저 설정에 따라 ReferrerUrl 이 생략될 수 있음 → 실험 필요.
* OpenSavePidlMRU / LastVisitedPidlMRU (NTUSER.DAT `Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32`)
  - 공용 '열기/저장' 대화상자에서 선택한 파일(확장자별)과 그 대화상자를 띄운 실행파일(chrome.exe 등)을 기록.
  - 브라우저 파일 업로드 정황(SAI-004)의 핵심 보강 증거 후보. 파싱: RECmd (ComDlg32 플러그인) / Registry Explorer.
* $Recycle.Bin ($I / $R): 삭제(SAI-009) 시 원래 경로·삭제 시각 복구. RBCmd 로 파싱.
* Prefetch / Amcache: 다운로드한 AI 생성물 실행(SAI-006)·AI 앱 실행(SAI-007)의 실행 흔적 보강. PECmd / AmcacheParser.

## 3-2. PoC 연동
* `collector/collect_artifacts.ps1` 이 LECmd·JLECmd·MFTECmd 를 실행해 분석 엔진 입력 폴더를 만든다.
* 엔진은 EZ Tools CSV 를 헤더로 자동 판별한다 (`python -m shadow_ai_forensics detect <폴더>`).
* 실험 절차와 기록 양식은 [results.md](results.md) 참고.

## 4. 참고 자료
* Eric Zimmerman's Tools (MFTECmd, LECmd, JLECmd, RECmd, PECmd, RBCmd) https://ericzimmerman.github.io/
* SANS, *Windows Forensic Analysis* 포스터 — LNK/JumpList/ShellBags/ComDlg32 아티팩트 의미 https://www.sans.org/posters/windows-forensic-analysis/
* Microsoft, Change Journal(USN) 레코드 및 Reason 플래그 https://learn.microsoft.com/windows/win32/api/winioctl/ns-winioctl-usn_record_v2
* Microsoft, Mark of the Web / Zone.Identifier 개요 https://learn.microsoft.com/deployedge/per-site-configuration-by-policy

