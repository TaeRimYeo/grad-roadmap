# 프로젝트: 학기 로드맵 자동 설계기

## 목적
학생 이수 내역 + 학과 졸업요건 → CP-SAT로 학기별 수강 로드맵 자동 생성

## 절대 규칙
- AI API(LLM, 외부 추천 모델)를 절대 사용하지 않는다. 모든 판정은 규칙과 제약 최적화로만 한다
- solver.py 는 fastapi 를 import 하지 않는다 (로직과 API 분리)
- DB 스키마는 다학과·다학번 구조를 유지한다
- 한 번에 여러 파일을 고치지 말고 한 단계씩 진행한다

## 기술 스택
- backend: Python 3.12, FastAPI, SQLAlchemy, OR-Tools CP-SAT, Neon(PostgreSQL)
- frontend: React 19 + TypeScript + Vite + Tailwind CSS v4 (Figma Make 시안 기반)
- 디자인 규칙은 frontend/DESIGN.md 를 따른다. 새 색상·폰트 크기 임의 추가 금지
- 원본 데이터: backend/data/ (courses.csv, sections.csv, prerequisites.csv, requirements.json)

## 학과 도메인 (경기과학기술대학교 컴퓨터모바일융합과)
- 학위과정: 전문학사(주간 6학기) / 전공심화(야간 2학기, 전문학사 취득 후)
- 세부전공: SW융합전공 / 게임개발전공 / 공통. 타 전공 과목도 수강 가능(soft 제약)
- 졸업요건: 총 110학점, 전공(전필+전선) 64학점 이상, 전공필수 3과목(정보처리특론·캡스톤디자인1·캡스톤디자인2), 교양 최소요건 없음
- 학기 학점: 15~22학점. 본인의 마지막 학기만 최소 10학점 (마지막 학기는 학생마다 다름 → docs/솔버_학점제약_메모.md)
- 선수과목: '기초 → 응용' 관계 + 캡스톤디자인1 → 2

## 도메인 용어
- placeholder(가상 과목): 교양처럼 과목명을 특정할 수 없을 때 쓰는 "N학점짜리 빈 자리". is_placeholder=true
- 진단(diagnose): 무엇을 더 들어야 하는지 계산. 솔버 미사용
- 로드맵(roadmap): 학기별 배치 계산. CP-SAT 사용

## 팀
- 3인 팀, 초보자. 코드에 한국어 주석을 충분히 달 것
- 어려운 개념은 먼저 설명하고 코드를 보여줄 것