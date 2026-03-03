# Nokia Config IP Manager

Nokia SR OS 장비의 config 파일을 파싱하여 IP 관리대장을 자동으로 생성하는 웹 대시보드입니다.

---

## Overview

네트워크 엔지니어가 수십~수백 개의 Nokia SR OS config 파일을 수동으로 분석하지 않아도, 폴더를 선택하는 것만으로 전체 IP 현황을 자동 집계하고 Excel/CSV로 내보낼 수 있습니다.

**주요 처리 대상:**
- **System IP** (Loopback `/32`)
- **Interface IP** (물리 포트, LAG 포트)
- **Static Route** (목적지 CIDR + Next-hop)

Peer 장비는 Next-hop IP 역방향 매핑과 인터페이스 Description 패턴 분석을 통해 자동 식별됩니다.

---

## Features

- 📁 **로컬 폴더 업로드** — 사용자 PC의 config 폴더를 브라우저에서 직접 선택
- 🔍 **실시간 검색 & 필터** — IP 유형별 탭 + 키워드 검색
- 📊 **통계 대시보드** — 장비 수, IP 수, 유형별 집계, 최신 Config 날짜
- ⚙️ **컬럼 커스터마이즈** — 표시 여부 토글 + 드래그로 순서 변경 (localStorage 영구 저장)
- 📤 **내보내기** — Excel (4개 시트: 전체/Interface IP/Static Route/장비 목록) & CSV
- 🐳 **Docker 지원** — `docker-compose up` 한 줄로 실행

---

## Parsed Data Fields

config 파일에서 추출하는 필드 목록입니다.

| 필드 | 설명 |
|------|------|
| CIDR | IP 주소 + Prefix (예: `192.0.2.1/30`) |
| IP 유형 | System IP / Interface IP / Static Route |
| 장비명 | config 내 `name` 값 |
| 장비 모델 | TiMOS 헤더에서 자동 감지 (Nokia 7210/7705/7750 등) |
| 위치 | config 내 `location` 값 |
| OS 버전 | TiMOS 버전 (예: `TiMOS-B-7.0.R4`) |
| 인터페이스 | 인터페이스 이름 |
| 포트 | 물리 포트 또는 LAG 번호 |
| 설명 | 인터페이스/포트 description |
| Peer 장비 | Next-hop 역맵 또는 description 패턴으로 자동 추출 |
| Peer 포트 | Peer 장비의 연결 포트 |
| Next-hop IP | Static Route의 next-hop 주소 |
| 상태 | Active / Shutdown |
| Config 날짜 | 파일 생성 날짜 (`Generated` 헤더) |
| Router ID | BGP/OSPF Router ID |
| AS 번호 | Autonomous System 번호 |

---

## Tech Stack

| 구분 | 기술 |
|------|------|
| Backend | Python 3.11, Flask |
| Parser | 순수 Python (정규식 + 들여쓰기 기반 블록 파싱) |
| Frontend | Bootstrap 5.3, Bootstrap Icons, SortableJS |
| Export | openpyxl (Excel), csv |
| 인프라 | Docker, docker-compose |

---

## Prerequisites

**Docker 사용 시 (권장):**
- Docker Desktop

**로컬 실행 시:**
- Python 3.11+
- pip

---

## Getting Started

### Docker (권장)

```bash
git clone https://github.com/your-username/Nokia-Config-IP-Manager.git
cd Nokia-Config-IP-Manager

docker-compose up -d
```

브라우저에서 http://localhost:5001 접속 후 **폴더 선택** 버튼으로 config 폴더를 지정합니다.

> **Note:** `docker-compose.yml`의 volume 마운트(`../config:/config:ro`)는 서버 사이드 로딩용입니다.
> 브라우저에서 **폴더 선택** 버튼을 사용하면 마운트 없이도 로컬 PC의 폴더를 바로 업로드할 수 있습니다.

### 로컬 실행

```bash
git clone https://github.com/your-username/Nokia-Config-IP-Manager.git
cd Nokia-Config-IP-Manager

pip install -r requirements.txt
python app.py
```

---

## Usage

1. 브라우저에서 http://localhost:5001 접속
2. **폴더 선택** 클릭 → OS 파일 탐색기에서 config 파일이 있는 폴더 선택
3. 자동으로 파싱 후 IP 목록 표시
4. 상단 탭(전체 / System IP / Interface IP / Static Route)으로 필터링
5. 검색창에서 키워드 검색
6. `⚙` 아이콘으로 컬럼 표시 여부 및 순서 조정
7. **Excel** 또는 **CSV** 버튼으로 내보내기

### Config 파일 형식

Nokia SR OS TiMOS 계열 장비의 config 파일을 지원합니다.

```
# TiMOS-B-7.0.R4 both/mpc ALCATEL SAS-M 7210 Copyright ...
# Generated WED JAN 21 03:31:37 2026 UTC
...
```

파일명 규칙: `{hostname}_{YYYYMMDD}.txt` (권장)

---

## Project Structure

```
Nokia-Config-IP-Manager/
├── app.py                  # Flask 애플리케이션 (API 라우트)
├── parser/
│   └── ip_parser.py        # Nokia SR OS config 파서
├── templates/
│   └── index.html          # 단일 페이지 대시보드 (Bootstrap 5)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .gitignore
```

---

## API Endpoints

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET` | `/` | 대시보드 페이지 |
| `POST` | `/api/upload` | config 파일 업로드 및 파싱 |
| `GET` | `/api/export/excel` | Excel 다운로드 |
| `GET` | `/api/export/csv` | CSV 다운로드 |

---

## Environment Variables

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SECRET_KEY` | 랜덤 생성 | Flask 세션 시크릿 키 |
| `CONFIG_DIR` | `../config` | 서버 사이드 config 기본 경로 |

---

## Roadmap

- [ ] nokia-config-visualizer 프로젝트와 통합
- [ ] VPRN / VPLS 인터페이스 파싱 지원
- [ ] IP 중복 검사 기능
- [ ] 변경 이력 비교 (이전 파싱 결과와 diff)

---

## License

This project is for internal use. All rights reserved.
