# 연구 주제
Shadow AI 탐지 및 이벤트 상관분석

## 1. 연구 목표
Windows 이벤트 및 포렌식 아티팩트를 연결하여 Shadow AI 사용 행위를 탐지하고 재구성한다.

## 2. 기술 조사
- [x] Shadow AI 탐지 기술 및 한계 조사 → [results.md §1](results.md#1-shadow-ai-탐지-기술-및-한계)
- [x] 이벤트 정규화 및 Timeline 구조 설계 → [§2](results.md#2-이벤트-정규화-및-timeline-구조-설계), 코드 `src/shadow_ai_forensics/schema.py`
- [x] 상관분석 방식 조사 → [§3](results.md#3-상관분석-방식-조사)
- [x] 탐지 규칙 및 시나리오 5개 이상 정의 → [§4](results.md#4-탐지-규칙-및-시나리오-정의) (규칙 9개)
- [x] 가상 이벤트 기반 상관분석 PoC 구현 → [§5](results.md#5-가상-이벤트-기반-상관분석-poc), `tools/generate_synthetic.py`
- [x] 증거와 추론의 구분 및 오탐 가능성 검증 → [§6](results.md#6-증거와-추론의-구분-및-오탐-가능성)
- [ ] 실제 Windows VM 데이터로 규칙 재검증 (02·04·05 실험 결과 반영 후)

## 3. 프로젝트 적용 가능성
- PoC 엔진(`python -m shadow_ai_forensics analyze`)이 7종 입력 형식을 자동 판별해 하나의 타임라인으로 정규화하고,
  AI 사용 세션을 기준점으로 9개 규칙을 적용해 HTML 리포트를 만든다.
- 규칙은 실제 도구(MFTECmd·LECmd·JLECmd·EvtxECmd·Chrome History) 출력 형식을 그대로 읽으므로,
  02~05 팀원의 실험 데이터를 넣으면 바로 검증할 수 있다.
- 남은 핵심 과제는 "가정한 아티팩트 동작"(예: 브라우저 파일 선택 시 LNK 생성 여부)을 실측으로 확인하는 것이다.
  가정 목록은 results.md §5.4 에 정리했다.

## 4. 참고 자료
- Gravitee, *Shadow AI Discovery Forensics* — 단일 신호로는 Shadow AI 를 식별할 수 없고 여러 증거를 교차해야 한다는 관점
  https://gravitee.io/corpus/gen-1964/computer-forensics/shadow-ai-discovery-forensics.html
- A. Fortuna, *Browser AI forensics* (2026) — 브라우저 내 AI 어시스턴트 아티팩트(IndexedDB 등) 교차 분석
  https://andreafortuna.org/2026/07/28/browser-ai-forensics/
- MITRE ATT&CK T1567 (Exfiltration Over Web Service), T1560.001 (Archive via Utility), T1070.004 (File Deletion)
- Plaso/log2timeline — 다중 아티팩트 슈퍼 타임라인 개념 https://plaso.readthedocs.io/
