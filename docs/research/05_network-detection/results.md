# 실험 결과

> 상태: **실험 설계 완료 / 실측 전**.

## 1. 실험 환경
- Windows 11 VM, Sysmon(collector/sysmon-shadowai.xml), DNS-Client/Operational 로그 활성화
  (`wevtutil sl Microsoft-Windows-DNS-Client/Operational /e:true`)
- Chrome·Edge (보안 DNS 기본값 기록), Wireshark(기준 데이터)

## 2. 실험 목적
- 서비스·행위 단계별 DNS 질의 지문을 확보해 카탈로그를 보정한다.
- DoH·QUIC·캐시 조건에서 엔드포인트 로그가 무엇을 놓치는지 측정한다.

## 3. 실험 과정
| ID | 조건 | 동작 | 측정 |
|---|---|---|---|
| N-1 | 기본 | 서비스별 접속 → 대화 → 업로드 → 다운로드 | 단계별 질의 도메인·프로세스 |
| N-2 | 기본 | 다른 사이트에서 AI 링크가 있는 페이지만 열기 | 프리페치로 인한 질의 발생 여부 (오탐 근거) |
| N-3 | 보안 DNS(DoH) 강제 | N-1 반복 | Sysmon EID 22 / DNS-Client 누락 여부 |
| N-4 | DNS 캐시 유지 상태 | 10분 간격 재접속 | 재질의 여부 → 세션 종료 추정 가능성 |
| N-5 | 기본 | 10MB 파일 업로드 | SRUM 송신 바이트 증가량 |
| N-6 | 기본 | Python 스크립트로 API 호출 | python.exe 귀속 확인 (api 채널) |

## 4. 실험 결과
| ID | 결과 | 카탈로그/규칙 반영 |
|---|---|---|
| N-1 | | |
| N-2 | | |
| N-3 | | |
| N-4 | | |
| N-5 | | |
| N-6 | | |

## 5. 확인된 한계

## 6. 추가 연구 사항
- SRUM 파서(SrumECmd CSV) 엔진 연동
