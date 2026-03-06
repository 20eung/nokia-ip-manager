# Nokia TiMOS Config 문법 레퍼런스

> Nokia SR OS (TiMOS) config 파일을 파싱할 때 알아야 할 OS 버전별 문법 차이를 정리한 문서입니다.
> 파서 개발 및 유지보수 시 참조하세요.

---

## 목차

1. [config 파일 구조 개요](#1-config-파일-구조-개요)
2. [파일 헤더 형식](#2-파일-헤더-형식)
3. [OS 버전 분류](#3-os-버전-분류)
4. [Router 블록 문법 차이](#4-router-블록-문법-차이)
5. [Interface 블록 문법](#5-interface-블록-문법)
6. [Static Route 문법 차이](#6-static-route-문법-차이)
7. [IES Service 블록 (BB/SR 장비)](#7-ies-service-블록-bbsr-장비)
8. [Port 명명 규칙](#8-port-명명-규칙)
9. [SAP 형식](#9-sap-형식)
10. [파일 인코딩 및 특수 케이스](#10-파일-인코딩-및-특수-케이스)
11. [Python 파싱 구현 예시](#11-python-파싱-구현-예시)
12. [장비 모델별 요약 매트릭스](#12-장비-모델별-요약-매트릭스)

---

## 1. config 파일 구조 개요

Nokia SR OS config 파일은 **4 스페이스 들여쓰기** 기반의 계층 블록 구조입니다.
탭 문자는 사용하지 않습니다.

```
# TiMOS-C-20.10.R13 cpm/hops64 Nokia 7750 SR Copyright ...
# Generated WED JAN 21 03:31:37 2026 UTC

exit all
configure
    system
        name "hostname"
        location "..."
    exit
    router Base
        interface "p1/1/1"
            address 10.0.0.1/30
            port 1/1/1
            no shutdown
        exit
    exit
    service
        ies 10 customer 1 create
            interface "pX/Y/Z" create
                address 192.168.0.1/30
                sap X/Y/Z create
                exit
            exit
        exit
    exit
exit all
```

블록 구조 규칙:
- 모든 블록은 `exit`로 닫힘
- 들여쓰기 깊이(indent)로 블록 계층 판단
- 주석 줄은 `#`으로 시작
- `echo "..."` 줄은 섹션 구분자 (파싱 무시)

---

## 2. 파일 헤더 형식

config 파일 첫 줄에 OS 버전과 장비 모델 정보가 있습니다.

### 2.1 표준 형식 (Nokia 브랜드 이후)

```
# TiMOS-C-20.10.R13 cpm/hops64 Nokia 7750 SR Copyright (c) 2000-2022 Nokia.
```

```
# TiMOS-B-22.3.R3 both/hops Nokia SAS-Sx 22F2C4SFP+ 7210 Copyright (c) 2000-2022 Nokia.
```

### 2.2 구버전 형식 (Alcatel-Lucent 브랜드)

```
# TiMOS-B-7.0.R4 both/mpc ALCATEL SAS-M 7210 Copyright (c) 2000-2015 Alcatel-Lucent.
```

### 2.3 7705SAR 특수 형식 ⚠️

Copyright가 **다음 줄**로 분리됩니다. 벤더명도 `ALCATEL-LUCENT`(하이픈 포함)입니다.

```
# TiMOS-B-6.1.R7 both/hops ALCATEL-LUCENT SAR 7705
# Copyright (c) 2000-2015 Alcatel-Lucent.
```

### 2.4 헤더 앞에 CLI 프롬프트가 있는 경우 ⚠️

터미널 출력을 직접 저장한 파일에서 첫 줄에 CLI 프롬프트가 포함될 수 있습니다.

```
A:hostname# admin display-config
# TiMOS-C-14.0.R6 cpm/hops64 Nokia 7750 SR Copyright ...
```

또는 BOM 문자 + 프롬프트:

```
﻿B:hostname# admin display-config
# TiMOS-C-14.0.R6 ...
```

**파싱 전략**: 첫 5~10줄을 순회하여 `# TiMOS-` 패턴을 찾아야 합니다. 첫 줄에만 의존하면 안 됩니다.

### 2.5 Generated 날짜 형식

```
# Generated THU MAR 05 16:00:14 2026 UTC
```

월은 영문 3자 약어(JAN~DEC), 시간은 UTC 기준.

---

## 3. OS 버전 분류

### 3.1 버전 명명 체계

```
TiMOS-{계열}-{메이저}.{마이너}.{패치}
         │
         ├── B: SAS/SAR 계열 (fixed-port, access)
         └── C: SR/ESS 계열 (chassis-based, core)
```

### 3.2 실제 환경의 OS 버전 목록

| OS 버전 | 장비 모델 | 브랜드 | 비고 |
|---------|----------|--------|------|
| TiMOS-B-6.1.R7 | Nokia 7705 SAR | ALCATEL-LUCENT | Copyright 다음 줄 |
| TiMOS-B-7.0.R4 | Nokia 7210 SAS-M, SAS-X | ALCATEL | - |
| TiMOS-B-8.0.R14 | Nokia 7210 SAS-Mxp | Nokia | - |
| TiMOS-B-12.0.R9 | Nokia 7750 SR | ALCATEL | - |
| TiMOS-B-14.0.R4/R6 | Nokia 7750 SR | Nokia | - |
| TiMOS-B-21.9.R1 | Nokia 7210 SAS-Mxp | Nokia | - |
| TiMOS-B-22.3.R3 | Nokia 7210 SAS-Sx | Nokia | - |
| TiMOS-B-23.9.R1 | Nokia 7210 SAS-Mxp | Nokia | - |
| TiMOS-B-24.9.R3 | Nokia 7210 SAS-Sx | Nokia | - |
| TiMOS-B-25.3.R1 | Nokia 7210 SAS-Mxp | Nokia | - |
| TiMOS-B-25.9.R1 | Nokia 7210 SAS-Sx | Nokia | - |
| TiMOS-C-12.0.R4 | Nokia 7750 SR | ALCATEL | - |
| TiMOS-C-12.0.R9 | Nokia 7750 SR, 7450 ESS | ALCATEL | - |
| TiMOS-C-14.0.R6 | Nokia 7750 SR | Nokia | IES 이중 블록 |
| TiMOS-C-20.10.R13 | Nokia 7750 SR | Nokia | router Base |
| TiMOS-C-22.7.R2 | Nokia 7750 SR | Nokia | router Base |

### 3.3 OS 버전 정규식

```python
# 구버전(ALCATEL), ALCATEL-LUCENT(7705SAR), 신버전(Nokia) 모두 지원
# Copyright가 같은 줄이거나 없는 경우(다음 줄) 모두 처리
RE_OS_VERSION = re.compile(
    r'# TiMOS-(\S+)\s+\S+\s+(?:ALCATEL-LUCENT|ALCATEL|Nokia)\s+(.+?)(?:\s+Copyright|\s*$)',
    re.IGNORECASE
)
```

추출 예시:
```python
# "# TiMOS-B-6.1.R7 both/hops ALCATEL-LUCENT SAR 7705 "
# → group(1) = "B-6.1.R7", group(2) = "SAR 7705"

# "# TiMOS-C-20.10.R13 cpm/hops64 Nokia 7750 SR Copyright ..."
# → group(1) = "C-20.10.R13", group(2) = "7750 SR"
```

---

## 4. Router 블록 문법 차이

### 4.1 신버전: `router Base` (TiMOS-C-20.x 이상, 일부 C-14.x)

```
    router Base
        interface "p1/1/1"
            address 10.0.0.1/30
            description "Trunk_to_peer"
            port 1/1/1
            no shutdown
        exit
        interface "system"
            address 10.0.0.100/32
            no shutdown
        exit
    exit
```

### 4.2 구버전: `router` (TiMOS-B 계열, TiMOS-C-12.x)

`Base` 키워드 없이 `router`만 사용. 뒤에 공백이 붙기도 함.

```
    router
        interface "p1/1/7"
            address 10.230.32.141/30
            port 1/1/7
            no shutdown
        exit
        interface "system"
            address 10.230.32.253/32
        exit
    exit
```

### 4.3 management router 블록 (무시 대상)

모든 버전에서 `router management` 블록이 먼저 나옵니다. 여기에는 IP 주소가 없으므로 파싱에서 건너뜁니다.

```
    router management
    exit

    router Base   ← 이 블록부터 파싱
        ...
    exit
```

### 4.4 파싱 전략

```python
# 'router' 또는 'router Base' 모두 처리 (strip 후 비교)
if trimmed in ('router', 'router Base'):
    in_router = True
    router_indent = indent
```

---

## 5. Interface 블록 문법

### 5.1 일반 Interface (router 블록 내부)

모든 버전에서 동일한 형식:

```
        interface "p1/1/1"
            address 10.0.0.1/30
            description "To_peer_device_P1/1/1"
            port 1/1/1
            ingress
                filter ip 10
            exit
            no shutdown
        exit
```

핵심 필드:
| 키워드 | 설명 | 필수 여부 |
|--------|------|-----------|
| `address X.X.X.X/N` | IP/prefix | 선택 (system만 없으면 Loopback) |
| `port X/Y/Z` | 물리 포트 바인딩 | 선택 |
| `description "..."` | 설명 | 선택 |
| `no shutdown` | 활성 상태 | 없으면 Shutdown으로 간주 |

### 5.2 LAG Interface

물리 포트 대신 LAG(Link Aggregation Group) 포트 사용:

```
        interface "LAG1"
            address 10.230.68.17/30
            description "LAG1_Trunk_peer_device"
            port lag-1
            no shutdown
        exit
```

`port lag-N` 형식 — 정규식: `r'^port\s+([\w/-]+)'`로 `lag-1` 그대로 추출.

### 5.3 System Interface (Loopback)

포트 바인딩 없이 IP만 있는 특수 인터페이스:

```
        interface "system"
            address 10.230.40.1/32
            no shutdown
        exit
```

---

## 6. Static Route 문법 차이

### 6.1 구버전 Inline 형식 (TiMOS-C-12.x 이하, BB 계열)

한 줄에 prefix + next-hop + 옵션이 모두 포함됩니다.

**기본형**:
```
        static-route 10.0.0.0/8 next-hop 10.1.1.1
```

**description 포함**:
```
        static-route 124.66.177.128/26 next-hop 124.66.189.78 description "SKGAS_IBS_Internet_5M_1"
```

**metric 포함**:
```
        static-route 124.66.178.0/24 next-hop 210.211.95.42 metric 10 description "Kakao_Ent_Internet_1"
```

**cpe-check 포함** (Nokia 전용 CPE 상태 확인):
```
        static-route 124.66.178.0/24 next-hop 124.66.189.66 cpe-check 124.66.189.66 drop-count 1 description "..."
```

**black-hole** (null route, IP 없음):
```
        static-route 10.0.0.0/8 black-hole description "For_deny_private"
```

### 6.2 신버전 블록 형식 (TiMOS-C-14.x 이상 일부)

prefix와 next-hop이 계층 블록으로 분리됩니다.

```
        static-route-entry 61.97.2.128/27
            next-hop 61.97.1.118
                description "SKME_Seosan_Naeoe_internet"
                no shutdown
            exit
        exit
```

### 6.3 두 형식을 구분하는 방법

| 구분 | 키워드 | 형식 |
|------|--------|------|
| 구버전 | `static-route` | inline (한 줄) |
| 신버전 | `static-route-entry` | block (계층) |

> **중요**: `static-route`와 `static-route-entry`는 다른 키워드입니다.
> `static-route-entry`를 먼저 검사하면 구분됩니다.

### 6.4 파싱 정규식

```python
# 신버전 블록 형식
RE_STATIC_ENTRY  = re.compile(r'static-route-entry\s+([\d.]+/\d+)')

# 구버전 inline 형식 (static-route-entry와 구분: 공백으로 시작)
RE_STATIC_INLINE = re.compile(r'^static-route\s+([\d.]+/\d+)\s+next-hop\s+([\d.]+)')

# inline description 추출 (줄 중간에 위치하므로 ^ 앵커 없이)
RE_INLINE_DESC   = re.compile(r'\bdescription\s+"([^"]+)"')
```

### 6.5 파싱 구현 예시

```python
def parse_static_routes(config_text: str) -> list[dict]:
    routes = []
    lines = config_text.split('\n')
    in_router = False
    current_prefix = None
    current_nh = None

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        indent = len(line) - len(line.lstrip())

        # router 블록 진입
        if not in_router and trimmed in ('router', 'router Base'):
            in_router = True
            router_indent = indent
            continue

        if not in_router:
            continue

        if trimmed == 'exit' and indent == router_indent:
            in_router = False
            continue

        # ① 구버전 inline 형식
        m = RE_STATIC_INLINE.match(trimmed)
        if m:
            m_desc = RE_INLINE_DESC.search(trimmed)
            routes.append({
                'prefix': m.group(1),
                'next_hop': m.group(2),
                'description': m_desc.group(1) if m_desc else '',
                'admin_state': 'Active',
            })
            continue

        # ② 신버전 블록 형식
        m = RE_STATIC_ENTRY.match(trimmed)
        if m:
            current_prefix = m.group(1)
            continue

        if current_prefix is None:
            continue

        m = RE_NEXT_HOP.match(trimmed)
        if m:
            current_nh = {
                'prefix': current_prefix,
                'next_hop': m.group(1),
                'description': '',
                'admin_state': 'Active',
            }
            continue

        # ... (description, shutdown 처리)

    return routes
```

---

## 7. IES Service 블록 (BB/SR 장비)

Nokia 7750 SR의 BB(Broadband) 장비는 인터페이스 IP를 `router Base`가 아닌
`service > ies` 블록 안에 정의합니다.

### 7.1 IES 블록 구조 (신버전: TiMOS-C-20.x)

```
    service
        customer 1 create
            description "Default customer"
        exit
        ies 10 customer 1 create
            interface "p1/1/4" create
                description "To-peer_device_P1/1/4"
                address 211.45.50.245/30
                icmp
                    no mask-reply
                exit
                sap 1/1/4 create
                    ingress
                        filter ip 10
                    exit
                exit
            exit
        exit
    exit
```

### 7.2 IES 이중 블록 구조 (구버전: TiMOS-C-14.x) ⚠️

동일한 `ies 10 customer 1 create`가 **두 번** 나타납니다.

- **첫 번째 블록**: 인터페이스 선언만 (address, SAP 없음)
- **두 번째 블록**: 실제 설정 (address, SAP, description 포함)

```
        ies 10 customer 1 create
            interface "p1/1/4" create    ← 선언만, 설정 없음
            exit
            interface "p1/1/2" create
            exit
        exit
        ies 10 customer 1 create         ← 실제 설정 블록
            interface "p1/1/4" create
                description "To-peer"
                address 211.45.50.245/30
                sap 1/1/4 create
                    ...
                exit
            exit
        exit
```

**파싱 전략**: 두 번째 블록이 덮어쓰거나, IP가 있는 인터페이스만 수집하면 자동으로 올바른 결과가 됩니다.

### 7.3 SAP 없는 IES Interface (포트 추론 필요) ⚠️

일부 인터페이스는 `address`만 있고 `sap` 블록이 없습니다.

```
            interface "p3/1/10" create
                description "DNS(SK-Net.com)#1_HA"
                address 168.154.224.2/25
                icmp
                    ...
                exit
                no shutdown
            exit
```

**포트 추론**: 인터페이스명이 Nokia 명명 규칙 `p{slot}/{mda}/{port}`를 따르면 이름에서 포트 번호를 추출할 수 있습니다.

```python
# 인터페이스명 → 포트 추론
_RE_IFACE_PORT = re.compile(r'^p(\d+/\d+/\d+(?:\.\d+)?)')
for iface in interfaces:
    if not iface.get('port') and iface.get('interface_name'):
        m = _RE_IFACE_PORT.match(iface['interface_name'])
        if m:
            iface['port'] = m.group(1)   # "p3/1/10" → "3/1/10"
```

### 7.4 IES 헤더 정규식

```python
# "ies 10 customer 1 create", "ies 20 customer 1 create" 등
RE_IES_HEADER = re.compile(r'^ies\s+\d+')

# "interface "p1/1/4" create" (IES 내부 인터페이스는 create 키워드 포함)
RE_IES_IFACE  = re.compile(r'^interface\s+"([^"]+)"\s+create')

# "sap 1/1/4 create"
RE_SAP_PORT   = re.compile(r'^sap\s+([\w/.-]+)\s+create')
```

---

## 8. Port 명명 규칙

### 8.1 물리 포트

형식: `{slot}/{mda}/{port}`

```
1/1/1    → 슬롯 1, MDA 1, 포트 1
3/1/23   → 슬롯 3, MDA 1, 포트 23
2/2/4    → 슬롯 2, MDA 2, 포트 4
```

### 8.2 서브 포트 (채널화)

형식: `{slot}/{mda}/{port}.{channel}`

```
1/4/12.1 → 슬롯 1, MDA 4, 포트 12, 채널 1
```

### 8.3 LAG 포트

형식: `lag-{N}`

```
lag-1
lag-2
lag-3
lag-4
```

router Base 내 interface의 `port` 필드에 직접 명시:
```
        interface "LAG1"
            port lag-1
```

### 8.4 인터페이스 명명 패턴

Nokia 장비는 인터페이스명과 포트명이 대응됩니다:

| 인터페이스명 | 포트 | 비고 |
|------------|------|------|
| `"p1/1/4"` | `1/1/4` | 일반 물리 포트 |
| `"p3/1/10"` | `3/1/10` | SAP 없을 때 이름으로 추론 |
| `"LAG1"` | `lag-1` | 명시적 `port lag-N` |
| `"system"` | (없음) | Loopback |

---

## 9. SAP 형식

SAP(Service Access Point)는 IES 서비스에서 물리 포트와 서비스를 연결합니다.

### 9.1 기본 SAP

```
                sap 1/1/4 create
                exit
```

### 9.2 VLAN Tagged SAP (채널화 포트)

형식: `{slot}/{mda}/{port}.{channel}:{vlan-id}`

```
            sap 1/4/12.1:100 create
            sap 1/4/1.1:106 create
            sap 1/4/3.1:22 create
```

### 9.3 SAP 포트 추출 정규식

```python
# 일반 SAP와 VLAN SAP 모두 지원
RE_SAP_PORT = re.compile(r'^sap\s+([\w/.-]+(?::\d+)?)\s+create')
```

---

## 10. 파일 인코딩 및 특수 케이스

### 10.1 줄 끝 문자

Nokia 장비는 Windows 줄 끝(`\r\n`)을 사용합니다.

```python
# 파일 읽기 후 \r 제거 처리
line.rstrip('\r\n')
# 또는 split('\n') 후 각 줄에서 strip
```

### 10.2 UTF-8 BOM

일부 파일 앞에 UTF-8 BOM(`\xEF\xBB\xBF`, 문자 `\ufeff`)이 있습니다.

```python
# errors='replace' 옵션으로 읽으면 BOM이 문자로 디코딩됨
# BOM 제거: utf-8-sig 인코딩 사용
config_text = path.read_text(encoding='utf-8-sig', errors='replace')
# 또는
config_text = path.read_text(encoding='utf-8', errors='replace').lstrip('\ufeff')
```

### 10.3 CLI 프롬프트 접두어

```
A:hostname# admin display-config       ← A (Active) 상태 프롬프트
B:hostname# admin display-config       ← B (Standby) 상태 프롬프트
```

파싱 시 영향 없음 (TiMOS 헤더 탐색을 첫 10줄에서 수행하면 됨).

### 10.4 파일명 vs 호스트명 불일치

파일명의 장비명과 config 내부 `name "..."` 값이 다를 수 있습니다.

예시:
- 파일명: `SK-Net_GwanHun2F_7210SAS_MPLS_2_20260220.txt`
- config 내 hostname: `SK-Net_GwanHun2F_7750SR_MPLS_2`

**권장 전략**: 파일명이 아닌 config 내부 `name` 값을 장비 식별자로 사용하세요.

---

## 11. Python 파싱 구현 예시

### 11.1 OS 버전 파싱

```python
import re

RE_OS_VERSION = re.compile(
    r'# TiMOS-(\S+)\s+\S+\s+(?:ALCATEL-LUCENT|ALCATEL|Nokia)\s+(.+?)(?:\s+Copyright|\s*$)',
    re.IGNORECASE
)

def parse_os_version(config_text: str) -> tuple[str, str]:
    """
    Returns (os_version, raw_model)
    예: ("TiMOS-B-6.1.R7", "SAR 7705")
        ("TiMOS-C-20.10.R13", "7750 SR")
    """
    lines = config_text.split('\n')
    for line in lines[:10]:   # 첫 10줄에서 탐색
        m = RE_OS_VERSION.search(line)
        if m:
            os_ver = f'TiMOS-{m.group(1)}'
            raw_model = m.group(2).strip()
            return os_ver, raw_model
    return '', ''
```

### 11.2 모델명 정규화

```python
def normalize_model(raw_model: str) -> str:
    """
    raw_model을 "Nokia {번호} {계열}" 형태로 정규화
    예: "7750 SR"          → "Nokia 7750 SR"
        "SAS-M 7210"       → "Nokia 7210 SAS-M"
        "SAR 7705"         → "Nokia 7705 SAR"
        "SAS-Mxp 22F2C 4SFP+ 7210" → "Nokia 7210 SAS-Mxp"
    """
    parts = raw_model.split()
    # 4자리 이상 숫자로 시작하는 파트를 장비 번호로 인식
    num_part = next((p for p in parts if re.match(r'^\d{4}', p)), '')
    if not num_part:
        return f"Nokia {parts[0]}" if parts else 'Nokia'

    idx = parts.index(num_part)
    if idx > 0:
        series = parts[0]          # "SAS-M 7210" → SAS-M
    elif len(parts) > 1:
        series = parts[1]          # "7750 SR" → SR
    else:
        series = ''

    return f"Nokia {num_part} {series}".strip() if series else f"Nokia {num_part}"
```

### 11.3 Router 블록 파싱 (버전 통합)

```python
RE_IFACE_NAME = re.compile(r'^interface\s+"([^"]+)"')
RE_ADDRESS    = re.compile(r'^address\s+([\d.]+/\d+)')
RE_PORT_REF   = re.compile(r'^port\s+([\w/-]+)')
RE_DESCRIPTION = re.compile(r'^description\s+"([^"]+)"')

def parse_router_interfaces(config_text: str) -> list[dict]:
    """
    'router' 또는 'router Base' 블록의 인터페이스 IP 추출
    구버전/신버전 모두 동일 처리
    """
    interfaces = []
    lines = config_text.split('\n')
    in_router = False
    router_indent = -1
    current_iface = None
    iface_indent = -1

    for line in lines:
        raw = line.rstrip('\r\n')
        trimmed = raw.strip()
        if not trimmed:
            continue
        indent = len(raw) - len(raw.lstrip())

        # router 섹션 진입 (구버전: 'router', 신버전: 'router Base')
        if not in_router and trimmed in ('router', 'router Base'):
            in_router = True
            router_indent = indent
            continue

        if not in_router:
            continue

        # router 섹션 종료
        if trimmed == 'exit' and indent == router_indent:
            if current_iface:
                interfaces.append(current_iface)
                current_iface = None
            in_router = False
            continue

        # interface 블록 시작
        if indent == router_indent + 4 and trimmed.startswith('interface "'):
            if current_iface:
                interfaces.append(current_iface)
            m = RE_IFACE_NAME.match(trimmed)
            if m:
                current_iface = {
                    'name': m.group(1),
                    'ip': '', 'port': '',
                    'description': '', 'admin_state': 'Shutdown',
                }
                iface_indent = indent
            continue

        if current_iface is None:
            continue

        # interface 블록 종료
        if trimmed == 'exit' and indent == iface_indent:
            interfaces.append(current_iface)
            current_iface = None
            continue

        m = RE_ADDRESS.match(trimmed)
        if m:
            current_iface['ip'] = m.group(1)
            continue

        m = RE_PORT_REF.match(trimmed)
        if m:
            current_iface['port'] = m.group(1)
            continue

        m = RE_DESCRIPTION.match(trimmed)
        if m:
            current_iface['description'] = m.group(1)
            continue

        if trimmed == 'no shutdown':
            current_iface['admin_state'] = 'Active'

    return interfaces
```

### 11.4 Static Route 통합 파싱

```python
RE_STATIC_ENTRY  = re.compile(r'static-route-entry\s+([\d.]+/\d+)')
RE_STATIC_INLINE = re.compile(r'^static-route\s+([\d.]+/\d+)\s+next-hop\s+([\d.]+)')
RE_INLINE_DESC   = re.compile(r'\bdescription\s+"([^"]+)"')
RE_NEXT_HOP      = re.compile(r'next-hop\s+([\d.]+)')

def parse_static_routes(config_text: str) -> list[dict]:
    """
    구버전 inline + 신버전 block 형식 모두 지원
    black-hole 타입은 next_hop이 없으므로 필터링
    """
    routes = []
    lines = config_text.split('\n')
    in_router = False
    router_indent = -1
    current_prefix = None
    prefix_indent = -1
    current_nh = None
    nh_indent = -1

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        indent = len(line) - len(line.lstrip())

        if not in_router and trimmed in ('router', 'router Base'):
            in_router = True
            router_indent = indent
            continue

        if not in_router:
            continue

        if trimmed == 'exit' and indent == router_indent:
            if current_nh:
                routes.append(current_nh)
            in_router = False
            current_prefix = None
            current_nh = None
            continue

        # ① 구버전 inline 형식: static-route X/Y next-hop A.B.C.D ...
        m = RE_STATIC_INLINE.match(trimmed)
        if m:
            if current_nh:
                routes.append(current_nh)
                current_nh = None
            m_desc = RE_INLINE_DESC.search(trimmed)
            routes.append({
                'prefix': m.group(1),
                'next_hop': m.group(2),
                'description': m_desc.group(1) if m_desc else '',
                'admin_state': 'Active',
            })
            current_prefix = None
            continue

        # ② 신버전 블록 형식: static-route-entry X/Y
        m = RE_STATIC_ENTRY.match(trimmed)
        if m:
            if current_nh:
                routes.append(current_nh)
                current_nh = None
            current_prefix = m.group(1)
            prefix_indent = indent
            continue

        if current_prefix is None:
            continue

        if trimmed == 'exit' and indent == prefix_indent:
            if current_nh:
                routes.append(current_nh)
                current_nh = None
            current_prefix = None
            continue

        m = RE_NEXT_HOP.match(trimmed)
        if m:
            if current_nh:
                routes.append(current_nh)
            current_nh = {
                'prefix': current_prefix,
                'next_hop': m.group(1),
                'description': '',
                'admin_state': 'Active',
            }
            nh_indent = indent
            continue

        if current_nh is None:
            continue

        if trimmed == 'exit' and indent == nh_indent:
            routes.append(current_nh)
            current_nh = None
            continue

        m = RE_DESCRIPTION.match(trimmed)
        if m:
            current_nh['description'] = m.group(1)
            continue

        if trimmed == 'shutdown':
            current_nh['admin_state'] = 'Shutdown'

    return routes
```

---

## 12. 장비 모델별 요약 매트릭스

| 장비 모델 | OS 계열 | router 키워드 | Static Route 형식 | IES 사용 | 특이사항 |
|----------|---------|--------------|------------------|----------|---------|
| Nokia 7705 SAR | TiMOS-B-6.x | `router` | inline | 없음 | ALCATEL-LUCENT, Copyright 다음 줄 |
| Nokia 7210 SAS-M/X | TiMOS-B-7.x | `router` | inline(드물) | 없음 | - |
| Nokia 7210 SAS-Mxp | TiMOS-B-8.x ~ B-25.x | `router` | - | 없음 | - |
| Nokia 7210 SAS-Sx | TiMOS-B-22.x ~ B-25.x | `router Base` | - | 없음 | - |
| Nokia 7750 SR | TiMOS-B-12.x, C-12.x | `router` | inline | 없음 | - |
| Nokia 7750 SR (BB) | TiMOS-C-12.x ~ C-14.x | `router` | inline | ✅ IES 이중 블록 | SAP 없는 인터페이스 |
| Nokia 7750 SR | TiMOS-C-14.x | `router Base` | block(entry) | ✅ | IES 이중 블록 구조 |
| Nokia 7750 SR | TiMOS-C-20.x ~ C-22.x | `router Base` | block(entry) | ✅ | - |
| Nokia 7450 ESS | TiMOS-C-12.x | `router` | - | 없음 | LAG 포트 다수 |

> **범례**:
> - Static Route 형식 `inline` = `static-route X/Y next-hop A.B.C.D`
> - Static Route 형식 `block(entry)` = `static-route-entry X/Y { next-hop ... }`
> - `-` = 해당 장비에서 확인된 Static Route 없음

---

*최종 업데이트: 2026-03-06*
*분석 대상: Nokia-Config-IP-Manager 프로젝트 실제 config 파일 297개 (96개 장비)*
