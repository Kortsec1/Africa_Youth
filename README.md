# Shadow AI Forensics

## 프로젝트 개요

본 프로젝트는 Windows 환경에서 발생하는 Shadow AI 사용 행위를 탐지하고, 다양한 디지털 포렌식 아티팩트를 활용하여 사용자 행위를 재구성하는 시스템 개발을 목표로 합니다.

기존의 AI 서비스 접속 여부 중심 탐지에서 확장하여, 파일 접근·수정, Clipboard, 브라우저 및 프로세스 활동을 시간순으로 연결하고 데이터 이동 정황을 분석합니다.

## 주요 기능

### 1. Shadow AI 사용 탐지
- ChatGPT 등 생성형 AI 서비스 접근 탐지
- Clipboard 및 사용자 행위 정보 수집
- AI 사용 관련 이벤트 식별

### 2. Windows 포렌식 아티팩트 분석
- `$MFT`, `$UsnJrnl`
- LNK, JumpList
- Browser History
- Process 및 사용자 활동 정보

### 3. 사용자 행위 재구성
- 서로 다른 아티팩트의 시간 정보 통합
- AI 사용 전후 파일 활동 분석
- 이벤트 간 상관관계 분석
- 증거 기반 Timeline 생성

### 4. 분석 결과 시각화
- Shadow AI 사용 이벤트 조회
- 사용자 행위 Timeline
- 관련 포렌식 증거 확인

## 시스템 구성 (예정)

Windows Endpoint
→ 이벤트 및 아티팩트 수집
→ 데이터 정규화
→ 상관분석 엔진
→ 탐지 결과 및 Timeline 시각화

## 현재 진행 단계

**1단계: 기술 조사 및 구현 가능성 검증**

현재는 각 Windows 아티팩트의 수집 가능성과 Shadow AI 사용 행위 재구성 가능성을 조사하고 있습니다.

향후 실제 실험 결과를 바탕으로 분석 대상과 구현 범위를 구체화할 예정입니다.

## 연구 분야

| 분야 | 주요 내용 |
|---|---|
| Windows Forensics | 파일 시스템 및 사용자 활동 아티팩트 |
| Browser / AI Forensics | AI 서비스 접근 및 사용 흔적 |
| Endpoint Telemetry | Clipboard, Process, Foreground Window |
| Shadow AI Detection | 기존 탐지 기술 및 사용 시나리오 |
| Correlation | Timeline 및 이벤트 상관분석 |

## 프로젝트 목표

단순히 AI 서비스에 접속했는지를 탐지하는 것이 아니라,

**AI 서비스 사용 전후에 사용자가 어떤 행동을 했는지 포렌식 증거를 기반으로 설명할 수 있는 시스템을 구현하는 것**이 최종 목표입니다.
