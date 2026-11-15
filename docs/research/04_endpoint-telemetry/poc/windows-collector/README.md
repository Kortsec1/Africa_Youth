# Windows 수집 PoC

## 구성

- Program.cs: Clipboard·활성창·WMI 프로세스 수집 및 JSONL 저장.
- RealtimeCollector.csproj: .NET8 Windows Forms, System.Management8.0.0.
- validation/file-test.ps1: 합성 파일 작업의 자동 시험.
- validation/process-etw-test.ps1: 관리자 ETW/프로세스 비교. Windows 전체 프로세스 메타데이터가 포함될 수 있다.

과거 수정본 빌드·실행 증거는 [결과보고서](../../results.md)에 있다. 게시를 위해 이번에 새 실행을 수행하지 않았다. 원본 환경에는 Smart App Control 차단이 있어 현재 재실행 가능을 보장하지 않는다.

## 준비 및 실행

Windows 데스크톱 세션, .NET8 SDK, 최초 NuGet 복원 연결, 합성 데이터가 필요하다. 정책상 허용된 환경에서 이 폴더를 기준으로:

```powershell
dotnet build -c Release
.\bin\Release\net8.0-windows\RealtimeCollector.exe --seconds 60 --out .\logs\test-01
```

제목 옵션: --window-titles. 기본120초, 지정시간 후 종료. Ctrl+C 조기종료 지원. 콘솔 강제종료 시 마지막 기록을 보장하지 않는다. 원문·키 입력·네트워크 전송·자동시작 기능은 없다. 창 제목 옵션은 문서명 등을 포함할 수 있다.

원본 PC에서 일반 권한 WMI 구독은 실패하고 관리자 실험은 성공했다. source_status를 소스별로 확인한다. 관리자 실행은 애플리케이션 제어 정책 우회 수단이 아니다. 차단 시 실행을 중지하고 승인된 환경을 사용한다.

## 결과 확인

실행에 표시된 정확한 파일 하나를 선택한다. 여러 실행을 와일드카드로 합치지 않는다.

```powershell
$logPath = '.\logs\test-01\실제로생성된파일.jsonl'
$rows = @(Get-Content -LiteralPath $logPath | ForEach-Object { $_ | ConvertFrom-Json })
$rows | Where-Object type -eq 'source_status' | ConvertTo-Json -Depth 8
$rows | Where-Object type -eq 'collector_error' | ConvertTo-Json -Depth 8
$rows | Where-Object type -eq 'collector_stop' | ConvertTo-Json -Depth 8
```

종료코드0·queue_drops0만으로 모든 소스 성공/무손실을 선언하지 않는다.

## 한계와 게시 원칙

schema_version2. Clipboard 재시도 최대5회/25ms, 조회 불가 null. 프로세스 종료의 PID·이름 연결은 후보이며 instance_identity_verified=false. 파일I/O·Security로그·ETW 직접소비는 C#본체에 미구현. ETW는 별도 스크립트다.

본체 로그에는 장치명·사용자SID·프로세스 정보가 포함될 수 있다. 생성한 원시 로그·ETL·진단파일은 Git에 추가하지 말고 [공유 증거 안내](../../evidence/README.md)에 따라 검토한다.
