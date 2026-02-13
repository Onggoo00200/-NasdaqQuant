# Development Journal: Nasdaq Quant Master Project

이 문서는 프로젝트 개발 과정에서의 주요 결정 사항과 기술적 해결책을 기록한 일지입니다.

## 📅 프로젝트 시작: 2026-02-14

### 1. 핵심 목표
- 건실한 퀀트 데이터(Z-Score, Rule of 40)와 LLM 기반의 투자 서사(Narrative)를 결합한 차세대 투자 분석 리포트 엔진 구축.

### 2. 주요 기술적 결정 및 해결 과제

#### 🚀 퀀트 엔진 고도화 (Aggregator & Logic)
- **데이터 소스 다각화**: `yfinance`의 데이터 누락 문제를 해결하기 위해 `ChoiceStock` 스크래핑 데이터와 `Raw Financials`(TTM 직접 계산)를 결합한 3단계 우선순위 수집 로직을 도입함.
  - **Priority**: 1. yf.info → 2. ChoiceStock → 3. Raw Financials (TTM)
- **단위 보정 (Unit Normalization)**: 서로 다른 데이터 소스(달러 vs 백만 단위) 간의 충돌로 인해 발생한 수치 왜곡(예: NVDA의 Profit Quality가 13억 배로 산출됨)을 해결하기 위해 모든 지표를 **Margin(%) 기반으로 정규화**함.
- **수익의 질(Profit Quality)**: 단순히 당기순이익이 아닌, 실제 현금흐름(CFO)이 영업이익 대비 어느 정도인지를 추적하여 '장부상 이익'의 신뢰도를 평가함.

#### 🤖 LLM 연동 (Narrative Report)
- **모델 선택**: `gemini-2.0-flash` (또는 `gemini-flash-latest`)를 사용하여 비용 효율적이고 빠른 분석 결과 생성.
- **분석 로직 분리**: `quant_logic.py`(숫자 분석)와 `llm_reporter.py`(서사 작성)를 분리하여 데이터가 없어도 AI가 임의로 수치를 지어내지 못하도록 강제함.
- **데이터 부족 사유 명시**: 지표가 없을 때 억지로 점수를 주지 않고 "데이터 부족" 사유를 리포트에 명시하여 분석의 투명성을 높임.

#### 🛠 시스템 환경 구축
- **Windows 환경 최적화**: PowerShell의 인코딩 문제를 피하기 위해 최종 리포트를 UTF-8 기반의 `.md` 파일로 저장하도록 구현.
- **Git 자동화**: 프로젝트 내에서 직접 Git을 설치하고 원격 저장소(`-NasdaqQuant`)를 연결하여 배포 프로세스를 구축함.

### 3. 향후 과제 (Backlog)
- [ ] Streamlit 기반 대시보드 인터페이스 연동.
- [ ] 다중 종목 비교 분석 기능 및 섹터별 가중치 차별화.
- [ ] 백테스팅 엔진과의 연동을 통한 Alpha Score 유효성 검증.

---
*이 문서는 개발자와 AI 에이전트 간의 협업을 통해 작성되었습니다.*
