# 최종 발표 구성안

## 1. 제목

TLS 기반 HTTPS 필터링 환경에서의 SNI 기반 정책 프록시와 한계 분석

## 2. 발표 흐름

1. 프로젝트 배경
   - HTTPS 트래픽 증가
   - TLS 복호화 없이 관찰 가능한 ClientHello와 SNI
   - SNI 기반 필터링의 활용과 한계

2. 프로젝트 목표
   - TLS Handshake와 SNI 구조 정리
   - SNI 기반 필터링 및 관련 우회·회피 개념 분석
   - 로컬 경량 정책 프록시 구현
   - 연결 성공, 차단 결과, 성능 로그 검증

3. 안전 범위
   - 로컬 테스트 도메인만 사용
   - 실제 차단 사이트 우회 실험 금지
   - VPN, 범용 프록시, 터널링 기능 미구현
   - TLS 복호화와 MITM 기능 미구현

4. 시스템 구조
   - Client
   - Policy Proxy `127.0.0.1:9443`
   - Test HTTPS Server `127.0.0.1:8443`
   - JSONL Logs

5. 구현 내용
   - ClientHello/SNI 파서
   - YAML 정책 로더
   - allow/block 정책 엔진
   - TCP 릴레이
   - 연결 로그 기록
   - pytest 단위 및 통합 테스트

6. 실험 시나리오
   - `allowed.test` 허용
   - `blocked.test` 차단
   - `unknown.test` 기본 차단
   - SNI 없는 연결 차단
   - 비정상 ClientHello 처리
   - upstream 장애 로그 기록
   - 동시 연결 처리

7. 실험 결과
   - 수동 시나리오 성공
   - pytest 12개 통과
   - 로그로 SNI, decision, error, byte count 확인
   - tcpdump pcap 캡처는 sudo 권한 문제로 별도 수동 수행 필요

8. 한계 분석
   - SNI 미제공 또는 비정상 ClientHello
   - ECH 적용 시 SNI 가시성 저하
   - QUIC/HTTP/3의 다른 관찰 구조
   - SNI와 HTTP Host/URL의 불일치 가능성
   - DNS 암호화와 보조 관찰 지점 약화

9. 결론
   - 로컬 환경에서 SNI 기반 정책 프록시를 구현하고 검증했다.
   - 허용, 차단, 기본 차단, 장애 상황을 로그로 확인했다.
   - SNI 기반 필터링은 단순하고 빠르지만, ECH/QUIC/정책 설계에 따른 구조적 한계가 있다.

## 3. 발표 자료에 넣을 표

| 구분 | 내용 |
| --- | --- |
| 분석 대상 | TLS ClientHello, SNI, ECH, QUIC/HTTP/3 |
| 구현 대상 | 로컬 SNI 정책 프록시 |
| 실험 대상 | `allowed.test`, `blocked.test`, `unknown.test` |
| 검증 항목 | 연결 성공, 차단, 기본 정책, 오류 처리, 동시 연결 |
| 결과물 | 분석 문서, 프록시 코드, 테스트 보고서, 시연 스크립트 |

## 4. 시연 체크리스트

- 가상환경 활성화
- 인증서 생성
- HTTPS 테스트 서버 실행
- 정책 프록시 실행
- 허용/차단/unknown 테스트 실행
- 로그 확인
- 테스트 보고서와 연결해 결과 설명
