# CTF Solver Agent — GPT Pro Code Review Request

## 프로젝트 개요
Multi-model CTF Solver Agent. Python 3.12+, asyncio, Click CLI, Textual TUI, Pydantic, aiodocker.

3개 AI Provider (Claude/Codex/z.ai)를 병렬로 돌려서 CTF 문제를 푸는 에이전트.
각 solver는 Docker 샌드박스에서 격리되어 실행, 도구(bash, 파일 I/O, web_fetch 등)를 사용.

## 아키텍처
- `cli.py`: Click CLI + TUI 분기 + SIGINT
- `solver/swarm.py`: ChallengeSwarm — 병렬 solver 오케스트레이션
- `solver/coordinator.py`: CoordinatorAgent — LLM 기반 전략 가이던스
- `providers/claude.py`: Anthropic Messages API (httpx)
- `providers/zai.py`: OpenAI-compatible REST (httpx)
- `providers/codex.py`: JSON-RPC subprocess
- `providers/base.py`: ProviderBase, SolverSession, ToolCall, ToolResult
- `sandbox/docker.py`: DockerSandbox (aiodocker)
- `sandbox/host.py`: HostSandbox (--no-docker)
- `tools/core.py`: bash, read_file, write_file, submit_flag, web_fetch 등
- `tools/vision.py`: view_image (multimodal)
- `tools/flag.py`: regex flag extraction
- `events.py`: EventBus (async pub/sub)
- `hint_server.py`: HTTP hint endpoint
- `config.py`: Pydantic Settings
- `tracing.py`: JSONL event log
- `collaboration/message_bus.py`: inter-solver insight sharing
- `collaboration/loop_detect.py`: loop detection (warn→break)
- `tracking/cost_tracker.py`: token/cost tracking
- `tracking/circuit_breaker.py`: per-provider circuit breaker
- `session_state.py`: session persistence + --resume
- `writeup.py`: solve-detail.md / solve-brief.md

## 이전 리뷰에서 수정한 32개 이슈
### Critical (8)
1. ToolCall/ToolResult: call_id/tool_use_id를 dataclass 필드로 승격 (동적 attribute 제거)
2. Claude: tool_use_id 정상 처리, httpx 재사용, session.close()
3. Z.AI: tool_call_id 포함, 기본 endpoint `api.z.ai/api/paas/v4/`, 모델 `glm-5.1`, httpx 재사용, session.close()
4. Codex: ToolResult.call_id / ToolCall(call_id=...) 사용
5. HostSandbox 신규 생성 (--no-docker)
6. 첫 LLM 호출: "Start solving." 전송
7. --files 모드: distfiles/ 하위디렉토리에 복사
8. aiodocker API: exec.start() Stream 반환 (await 불가), get_archive() TarFile 반환 (tuple 아님)

### Important (17)
9. Provider session.close() 구현 (Claude/ZAI)
10. httpx 클라이언트 재사용 (_get_client lazy pattern)
11. Config: claude_model, codex_model, zai_model 필드 추가
12. TOML [models] 섹션 지원
13. get_coordinator_provider 예외 처리
14. description.txt/YAML 자동 로딩
15. TUI 모드에서 coordinator 시작
16. _run_cli cleanup 예외 안전
17. LLM 호출에 글로벌 타임아웃 (asyncio.wait_for)
18. timeout_seconds 파라미터 매핑
19. 도구 실행 예외 래핑 (_execute_tool_inner)
20. view_image multimodal (inject_image → Claude base64 / ZAI data URI)
21. notify_coordinator event type → user_hint
22. SSRF DNS 리졸루션 차단 (socket.getaddrinfo)
23. EventBus unsubscribe + 큐 한도(1000) + QueueFull 드롭
24. Hint 서버 Content-Length 파싱 + wait_closed()
25. SIGINT 핸들러 단순화 (session state 제거)
26. Per-solver consecutive_errors (SolverInstance 필드)

### Minor (2)
27. Tracing: json.dumps(default=str)
28. submit_flag: "Flag candidate matches pattern" 문구

## 검증 요청사항
다음 항목을 집중적으로 검증해주세요:

1. **실제 실행 경로**: 단위 테스트는 통과하지만, 실제 Claude/Z.AI API 호출 시 프로토콜이 정확한지
2. **경쟁 상태 (Race Condition)**: asyncio 기반 병렬 실행에서 lock, event 순서
3. **리소스 누수**: Docker 컨테이너, httpx client, 파일 핸들러
4. **에러 처리**: 예외가 적절히 전파되는지, solver가 조용히 죽지 않는지
5. **보안**: SSRF, 명령어 인젝션, 컨테이너 탈출
6. **비용 추적 정확성**: token counting, pricing 계산
7. **Codex JSON-RPC 프로토콜**: request/response id 매칭, deadlock 가능성
8. **메모리**: EventBus queue, message_bus findings 무한 증가
9. **TUI/CLI 통합**: 이벤트 라우팅, coordinator 연결
10. **타입 안전성**: dataclass 필드, Protocol 준수

## 테스트 상태
- 120 passed, 1 skipped (Docker 통합 테스트 17개 포함)
- ruff 0 violations
- 커버리지: 47% (TUI/swarm 낮음)

## 파일 구조
```
src/ctf_solver/
├── __init__.py
├── cli.py                    # Click CLI + TUI 분기
├── config.py                 # Pydantic Settings
├── events.py                 # EventBus (pub/sub)
├── hint_server.py            # HTTP hint server
├── prompts.py                # System prompt builder
├── tracing.py                # JSONL tracer
├── session_state.py          # Session persistence
├── writeup.py                # Writeup generator
├── collaboration/
│   ├── loop_detect.py        # Loop detection
│   └── message_bus.py        # Inter-solver messaging
├── providers/
│   ├── __init__.py           # Provider registry
│   ├── base.py               # Protocol + data models
│   ├── claude.py             # Anthropic Messages API
│   ├── codex.py              # JSON-RPC subprocess
│   └── zai.py                # OpenAI-compatible REST
├── sandbox/
│   ├── __init__.py           # SandboxProtocol
│   ├── docker.py             # DockerSandbox
│   └── host.py               # HostSandbox
├── solver/
│   ├── __init__.py
│   ├── coordinator.py        # CoordinatorAgent
│   ├── solver_base.py        # Result types
│   └── swarm.py              # ChallengeSwarm
├── tools/
│   ├── core.py               # bash, file I/O, web, flag
│   ├── flag.py               # Flag extraction
│   └── vision.py             # Image viewing
├── tracking/
│   ├── circuit_breaker.py    # Per-provider breaker
│   └── cost_tracker.py       # Token/cost tracking
└── tui/                      # Textual TUI
tests/                        # 120 tests
```
