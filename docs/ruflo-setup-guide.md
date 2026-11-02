# Ruflo 내 PC 설치 가이드 (sideup 앱 개발용)

> Ruflo는 MIT 라이선스 무료 오픈소스입니다. 다만 안에서 호출하는 AI(Claude 등)의 사용량은 별도입니다.
> 공식 저장소: https://github.com/ruvnet/ruflo (npm 패키지명: `ruflo`)
> 아래 내용은 공식 README와 npm 메타데이터(ruflo 3.71.0 기준)로 확인한 것입니다. 버전은 바뀔 수 있으니 설치 전에 README를 한 번 더 확인하세요.

## 0. 사전 준비

| 항목 | 요구사항 | 확인 명령 |
|---|---|---|
| Node.js | **20 이상** | `node -v` |
| Claude Code | 설치되어 있어야 함 (Claude Code와 연동해 쓰는 도구) | `claude --version` |
| 터미널 | Mac/Linux 터미널, Windows는 PowerShell 또는 WSL | |

Node.js가 없거나 낮으면 https://nodejs.org 에서 LTS 버전을 설치하세요.

## 1. 설치 (가장 쉬운 방법)

sideup 프로젝트 폴더에서 실행합니다.

```bash
cd sideup
npx ruflo@latest init wizard
```

- 설정 마법사가 프로젝트에 필요한 파일을 만들어 줍니다.
- Windows PowerShell에서도 이 줄은 그대로 동작합니다.
- 설치가 끝나면 **Claude Code를 재시작**한 뒤 `/ruflo` 를 입력해 보세요.

처음에는 변경 내용을 미리 보고 싶다면 `--dry-run` 옵션이 있는지 `npx ruflo@latest init --help`로 확인하세요.

## 2. 대안: 전역 설치 / MCP 연결

```bash
# 전역 설치 (매번 npx 안 쳐도 됨)
npm install -g ruflo@latest

# Claude Code에 MCP 서버로 직접 연결
claude mcp add claude-flow -- npx ruflo@latest mcp start
```

## 3. 터미널 화면만 써보기 (Claude Code 없이)

```bash
npx ruflo tui
```

개요, 비용, 에이전트(swarm), 이벤트 화면을 볼 수 있습니다.

## 4. 처음 써볼 때 권장 순서

1. **연습용 브랜치를 먼저 만드세요.** `git checkout -b try-ruflo`
2. `init wizard`가 만든 파일 목록을 `git status`로 확인하세요.
3. 작은 작업(예: 버튼 하나 추가, 버그 하나 수정)부터 시켜 보세요.
4. 비용 화면(`npx ruflo tui`의 Cost)으로 사용량을 확인하세요.
5. 마음에 안 들면 `try-ruflo` 브랜치를 버리고 원래 브랜치로 돌아가면 됩니다. (그래서 1번이 중요합니다.)

## 5. 주의사항

- **비용**: 에이전트 여러 개를 동시에 돌리면 AI 사용량이 평소보다 빠르게 늡니다. 처음엔 작게 시작하세요.
- **가짜 주의**: 이름이 비슷한 다른 저장소가 많습니다. `ruvnet/ruflo` 또는 npm의 `ruflo`만 사용하세요.
- **민감 정보**: `.env`, API 키, 결제 키 등은 에이전트에게 보여주지 마세요.
- **옛 이름**: `claude-flow`가 예전 이름입니다. 문서에 `claude-flow`가 나와도 같은 프로젝트입니다.

## 6. 문제 해결

| 증상 | 해결 |
|---|---|
| `node` 버전 오류 | Node 20 이상으로 업그레이드 |
| `'bash' is not recognized` (Windows) | `curl ... \| bash` 대신 `npx ruflo@latest init wizard` 사용 |
| `/ruflo` 가 안 보임 | Claude Code를 완전히 종료 후 재시작 |
| 권한 오류(`EACCES`) | 전역 설치 대신 `npx` 방식 사용 |
