# Nokia Config IP Manager

> Nokia SR OS 장비의 config 파일을 파싱하여 IP 관리대장을 자동으로 생성하는 웹 대시보드

[![Version](https://img.shields.io/badge/Version-v1.2.0-blue)](https://github.com/20eung/nokia-ip-manager/releases/tag/v1.2.0)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![openpyxl](https://img.shields.io/badge/Export-Excel%20%7C%20CSV-217346?logo=microsoftexcel&logoColor=white)]()
[![License](https://img.shields.io/badge/License-Internal%20Use-lightgrey)]()

---

## Overview

네트워크 엔지니어가 수십~수백 개의 Nokia SR OS config 파일을 수동으로 분석하지 않아도, 폴더를 선택하는 것만으로 전체 IP 현황을 자동 집계하고 Excel/CSV로 내보낼 수 있습니다.

**주요 처리 대상:**
- **System IP** — Loopback (`/32`)
- **Interface IP** — 물리 포트, LAG 포트, IES 서비스 인터페이스
- **Static Route** — 목적지 CIDR + Next-hop + 출구 인터페이스 자동 추론

Peer 장비는 Next-hop IP 역방향 매핑과 인터페이스 Description 패턴 분석을 통해 자동 식별됩니다.

---

## Screenshot

![Dashboard](docs/images/dashboard.png)

---

## Features

- 📁 **로컬 폴더 업로드** — 사용자 PC의 config 폴더를 브라우저에서 직접 선택
- 🔍 **실시간 검색 & 필터** — IP 유형별 탭 + 키워드 검색
- 📊 **통계 대시보드** — 장비 수, IP 수, 유형별 집계, 최신 Config 날짜
- ⚙️ **컬럼 커스터마이즈** — 표시 여부 토글 + 드래그로 순서 변경 (localStorage 영구 저장)
- 📤 **내보내기** — Excel (4개 시트: 전체/Interface IP/Static Route/장비 목록) & CSV
- 🐳 **Docker 지원** — `docker-compose up` 한 줄로 실행
- 🔒 **폐쇄망 환경 완전 지원** — CDN 의존성 없이 정적 파일 내장
- 🗂️ **중복 파일 자동 처리** — 동일 장비의 날짜별 config 중 최신 파일만 파싱

### 파서 지원 기능

| 기능 | 상세 |
|------|------|
| **OS 버전 통합 파싱** | TiMOS-B(SAS/SAR)/C(SR/ESS) 전 버전, ALCATEL-LUCENT/ALCATEL/Nokia 벤더명 자동 감지 |
| **router 블록** | `router`(구버전) / `router Base`(신버전) 모두 지원 |
| **IES 서비스 인터페이스** | BB 장비의 `service > ies` 블록 파싱, 이중 블록 구조 처리 |
| **Static Route 형식** | inline(`static-route`, 구버전) + block(`static-route-entry`, 신버전) 동시 지원 |
| **Static Route 인터페이스 추론** | Next-hop IP → 로컬 서브넷 매핑으로 출구 인터페이스·포트 자동 식별 |
| **SAP 없는 인터페이스** | SAP 블록 미존재 시 인터페이스명(`p3/1/10`)에서 포트 번호 자동 추론 |
| **LAG 포트** | `lag-N` 형식 지원 |

---

## Supported Devices & OS Versions

| 장비 모델 | TiMOS 버전 | 비고 |
|----------|-----------|------|
| Nokia 7705 SAR | TiMOS-B-6.1.x | ALCATEL-LUCENT 벤더명, Copyright 다음 줄 형식 |
| Nokia 7210 SAS-M/X | TiMOS-B-7.0.x | ALCATEL 벤더명 |
| Nokia 7210 SAS-Mxp | TiMOS-B-8.0.x ~ B-25.x | Nokia 브랜드 이후 버전 포함 |
| Nokia 7210 SAS-Sx | TiMOS-B-22.x ~ B-25.x | |
| Nokia 7750 SR | TiMOS-B-12.x, C-12.x ~ C-22.x | MPLS/BB 장비 모두 지원 |
| Nokia 7450 ESS | TiMOS-C-12.x | LAG 포트 환경 |

> 파서 구현 상세 및 버전별 문법 차이는 [Nokia TiMOS Config 문법 레퍼런스](docs/nokia-timos-config-syntax.md)를 참조하세요.

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
| 포트 설명 | 포트 description |
| 인터페이스 설명 | 인터페이스 description |
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
| Frontend | Bootstrap 5.3, Bootstrap Icons, SortableJS (로컬 내장) |
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
git clone https://github.com/20eung/nokia-ip-manager.git
cd nokia-ip-manager

docker-compose up -d
```

브라우저에서 http://localhost:5001 접속 후 **폴더 선택** 버튼으로 config 폴더를 지정합니다.

> **Note:** `docker-compose.yml`의 volume 마운트(`../config:/config:ro`)는 서버 사이드 로딩용입니다.
> 브라우저에서 **폴더 선택** 버튼을 사용하면 마운트 없이도 로컬 PC의 폴더를 바로 업로드할 수 있습니다.

### 로컬 실행

```bash
git clone https://github.com/20eung/nokia-ip-manager.git
cd nokia-ip-manager

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

Nokia SR OS TiMOS 계열 장비의 config 파일(`admin display-config` 출력)을 지원합니다.

```
# TiMOS-C-20.10.R13 cpm/hops64 Nokia 7750 SR Copyright (c) 2000-2022 Nokia.
# Generated WED JAN 21 03:31:37 2026 UTC
...
```

파일명 규칙: `{hostname}_{YYYYMMDD}.txt` (권장)

동일 장비의 날짜별 파일이 여러 개 있을 경우 **가장 최신 파일만** 자동 선택됩니다.

---

## Project Structure

```
nokia-ip-manager/
├── app.py                  # Flask 애플리케이션 (API 라우트)
├── parser/
│   └── ip_parser.py        # Nokia SR OS config 파서
├── templates/
│   └── index.html          # 단일 페이지 대시보드 (Bootstrap 5)
├── static/
│   ├── css/                # Bootstrap, Bootstrap Icons (로컬 내장)
│   └── js/                 # Bootstrap Bundle, SortableJS (로컬 내장)
├── docs/
│   ├── images/             # README 스크린샷
│   └── nokia-timos-config-syntax.md  # TiMOS 버전별 문법 레퍼런스
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

## Documentation

| 문서 | 설명 |
|------|------|
| [Nokia TiMOS Config 문법 레퍼런스](docs/nokia-timos-config-syntax.md) | OS 버전별 config 문법 차이, 파싱 정규식, Python 구현 예시 |

---

## Roadmap

- [ ] nokia-config-visualizer 프로젝트와 통합
- [ ] VPRN / VPLS 인터페이스 파싱 지원
- [ ] IP 중복 검사 기능
- [ ] 변경 이력 비교 (이전 파싱 결과와 diff)

---

## License

This project is for internal use. All rights reserved.
