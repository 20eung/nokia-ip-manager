"""
Nokia SR OS Config IP Parser
parserV3.ts의 파싱 로직을 참고하여 Python으로 구현.
나중에 nokia-config-visualizer에 통합 시 이 파서를 TypeScript로 포팅하거나 API로 활용.
"""
import re
import os
from pathlib import Path
from ipaddress import IPv4Network, IPv4Address, AddressValueError
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
# 데이터 클래스 정의 (TypeScript interface에 대응)
# ─────────────────────────────────────────────

@dataclass
class IpRecord:
    """IP 관리대장 단일 레코드"""
    # IP 정보
    cidr: str               # 192.0.2.1/30
    ip_address: str         # 192.0.2.1
    prefix_length: int      # 30
    subnet_mask: str        # 255.255.255.252
    network_address: str    # 192.0.2.0

    # 분류
    ip_type: str            # System IP | Interface IP | Static Route

    # 장비 정보
    device_name: str        # Router-A_7210SAS_MPLS_1
    device_model: str       # Nokia 7210 SAS-M
    location: str           # Seoul DC Floor 1
    os_version: str         # TiMOS-B-7.0.R4
    config_date: str        # 2026-01-21

    # 인터페이스 / 라우팅 정보
    interface_name: str     # p1/1/7 | system | -
    port: str               # 1/1/7 | lag-1 | -
    interface_desc: str     # 인터페이스 자체 description
    port_desc: str          # 포트(물리) description

    # 연결 정보 (Peer)
    peer_device: str        # 상대편 장비명 (추출 또는 역방향 조회)
    peer_port: str          # 상대편 포트

    # Static Route 전용
    next_hop_ip: str        # next-hop IP (Static Route만 해당)
    route_desc: str         # static route description

    # 부가 정보
    admin_state: str        # Active | Shutdown
    router_id: str          # 장비의 Router ID
    as_number: str          # AS 번호
    filename: str           # 원본 파일명


# ─────────────────────────────────────────────
# 정규식 상수 (parserV3.ts 참고)
# ─────────────────────────────────────────────

RE_OS_VERSION     = re.compile(r'# TiMOS-(\S+)\s+\S+\s+(?:ALCATEL-LUCENT|ALCATEL|Nokia)\s+(.+?)(?:\s+Copyright|\s*$)', re.IGNORECASE)
RE_GEN_DATE       = re.compile(r'# Generated\s+\w+\s+(\w+)\s+(\d+)\s+[\d:]+\s+(\d{4})\s+UTC', re.IGNORECASE)
RE_HOSTNAME       = re.compile(r'^\s{4,8}name\s+"([^"]+)"')
RE_LOCATION       = re.compile(r'^\s+location\s+"([^"]+)"')
RE_SYSTEM_IP      = re.compile(r'interface\s+"system"[\s\S]*?address\s+([\d.]+/\d+)', re.IGNORECASE)
RE_ROUTER_ID      = re.compile(r'^\s+router-id\s+([\d.]+)')
RE_AS_NUMBER      = re.compile(r'^\s+autonomous-system\s+(\d+)')
RE_STATIC_ENTRY   = re.compile(r'static-route-entry\s+([\d.]+/\d+)')
RE_STATIC_INLINE  = re.compile(r'^static-route\s+([\d.]+/\d+)\s+next-hop\s+([\d.]+)')
RE_INLINE_DESC    = re.compile(r'\bdescription\s+"([^"]+)"')
RE_NEXT_HOP       = re.compile(r'next-hop\s+([\d.]+)')
RE_PORT_PHYSICAL  = re.compile(r'^port\s+(\d+/\d+/\d+(?:\.\d+)?)')
RE_PORT_LAG       = re.compile(r'^lag\s+(\d+)')
RE_IFACE_NAME     = re.compile(r'^interface\s+"([^"]+)"')
RE_ADDRESS        = re.compile(r'^address\s+([\d.]+/\d+)')
RE_SECONDARY      = re.compile(r'^secondary\s+([\d.]+/\d+)')
RE_PORT_REF       = re.compile(r'^port\s+([\w/-]+)')
RE_DESCRIPTION    = re.compile(r'^description\s+"([^"]+)"')
RE_IES_HEADER     = re.compile(r'^ies\s+\d+')
RE_IES_IFACE      = re.compile(r'^interface\s+"([^"]+)"\s+create')
RE_SAP_PORT       = re.compile(r'^sap\s+([\w/.-]+)\s+create')

# Peer 추출 정규식 (인터페이스/포트 description에서)
RE_PEER_TRUNK     = re.compile(r'Trunk[_\-]([A-Za-z0-9_\-]+?(?:MPLS|SAR|SAS|SR|BB|I)[\w\-]*)\s*(?:\(([^)]+)\))?', re.IGNORECASE)
RE_PEER_LAG       = re.compile(r'LAG\d+[_\-]Trunk[_\-]([A-Za-z0-9_\-]+?(?:MPLS|SAR|SAS|SR|BB|I)[\w\-]*)\s*(?:[_\-](P[\d/]+))?', re.IGNORECASE)
RE_PEER_TO        = re.compile(r'(?:^|[_\-])(?:To|to|TO)[_\-]([A-Za-z0-9_\-]+?(?:MPLS|SAR|SAS|SR|BB|I)[\w\-]*)', re.IGNORECASE)


# ─────────────────────────────────────────────
# 유틸리티 함수
# ─────────────────────────────────────────────

def prefix_to_mask(prefix_len: int) -> str:
    bits = (0xFFFFFFFF >> (32 - prefix_len)) << (32 - prefix_len)
    return '.'.join(str((bits >> (8 * i)) & 0xFF) for i in reversed(range(4)))


def get_network_address(cidr: str) -> str:
    try:
        net = IPv4Network(cidr, strict=False)
        return str(net.network_address)
    except (AddressValueError, ValueError):
        return ''


def is_ip_in_subnet(ip: str, cidr: str) -> bool:
    try:
        return IPv4Address(ip) in IPv4Network(cidr, strict=False)
    except (AddressValueError, ValueError):
        return False


def extract_peer_from_desc(desc: str) -> tuple[str, str]:
    """description 문자열에서 (peer_device, peer_port) 추출"""
    if not desc:
        return '', ''

    # 패턴 1: LAG{N}_Trunk_{장비명}_{포트}
    m = RE_PEER_LAG.search(desc)
    if m:
        return m.group(1), m.group(2) or ''

    # 패턴 2: Trunk_{장비명}({포트})  or  Trunk_{장비명}
    m = RE_PEER_TRUNK.search(desc)
    if m:
        return m.group(1), m.group(2) or ''

    # 패턴 3: {something}_To_{장비명}  or  To_{장비명}
    m = RE_PEER_TO.search(desc)
    if m:
        return m.group(1), ''

    return '', ''


def parse_model_from_os_comment(line: str) -> tuple[str, str]:
    """
    구버전: # TiMOS-B-7.0.R4 both/mpc ALCATEL SAS-M 7210 Copyright ...
    신버전: # TiMOS-C-22.7.R2 cpm/hops64 Nokia 7750 SR Copyright ...
           # TiMOS-B-23.9.R1 both/hops Nokia SAS-Mxp 22F2C 4SFP+ 7210 Copyright ...
    → os_version='TiMOS-B-7.0.R4', model='Nokia 7210 SAS-M' 형태로 정규화
    """
    m = RE_OS_VERSION.search(line)
    if not m:
        return '', ''
    os_ver = f'TiMOS-{m.group(1)}'
    raw_model = m.group(2).strip()

    # 숫자(장비 번호)를 찾아 "Nokia {번호} {계열}" 형태로 정규화
    # 예: "SAS-M 7210" → "Nokia 7210 SAS-M"
    # 예: "7750 SR" → "Nokia 7750 SR"
    # 예: "SAS-Mxp 22F2C 4SFP+ 7210" → "Nokia 7210 SAS-Mxp"
    parts = raw_model.split()
    num_part = next((p for p in parts if re.match(r'^\d{4}', p)), '')
    if num_part:
        idx = parts.index(num_part)
        if idx > 0:
            series = parts[0]          # 숫자 앞 계열명: "SAS-M 7210" → SAS-M
        elif len(parts) > 1:
            series = parts[1]          # 숫자 뒤 계열명: "7750 SR" → SR
        else:
            series = ''
        model = f"Nokia {num_part} {series}".strip() if series else f"Nokia {num_part}"
    else:
        model = f"Nokia {parts[0]}" if parts else 'Nokia'
    return os_ver, model


def parse_gen_date(config_text: str) -> str:
    """# Generated WED JAN 21 03:31:37 2026 UTC → '2026-01-21'"""
    m = RE_GEN_DATE.search(config_text)
    if not m:
        return ''
    month_map = {
        'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
        'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
        'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
    }
    month = month_map.get(m.group(1).upper(), '00')
    day = m.group(2).zfill(2)
    year = m.group(3)
    return f'{year}-{month}-{day}'


# ─────────────────────────────────────────────
# 파싱 함수
# ─────────────────────────────────────────────

def extract_device_info(config_text: str, filename: str) -> dict:
    """장비 기본 정보 추출"""
    info = {
        'filename': filename,
        'hostname': '',
        'os_version': '',
        'model': '',
        'location': '',
        'config_date': parse_gen_date(config_text),
        'system_ip': '',
        'router_id': '',
        'as_number': '',
    }

    lines = config_text.split('\n')

    for line in lines[:10]:
        os_ver, model = parse_model_from_os_comment(line)
        if os_ver:
            info['os_version'] = os_ver
            info['model'] = model
            break

    for line in lines:
        if not info['hostname']:
            m = RE_HOSTNAME.match(line)
            if m:
                info['hostname'] = m.group(1)
        if not info['location']:
            m = RE_LOCATION.match(line)
            if m:
                info['location'] = m.group(1)
        if info['hostname'] and info['location']:
            break

    # System IP (parserV3.ts extractSystemIp 참고)
    m = RE_SYSTEM_IP.search(config_text)
    if m:
        info['system_ip'] = m.group(1).split('/')[0]

    # Router ID
    for line in lines:
        m = RE_ROUTER_ID.match(line)
        if m:
            info['router_id'] = m.group(1)
            break

    # AS 번호
    for line in lines:
        m = RE_AS_NUMBER.match(line)
        if m:
            info['as_number'] = m.group(1)
            break

    return info


def extract_port_descriptions(config_text: str) -> dict[str, str]:
    """
    물리 포트 description 추출
    parserV3.ts extractPortInfo() 참고
    포트명 → description 맵 반환
    """
    port_map: dict[str, str] = {}
    lines = config_text.split('\n')

    current_port = ''
    port_indent = -1
    in_ethernet = False
    ethernet_indent = -1

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        indent = len(line) - len(line.lstrip())

        if not current_port:
            m = RE_PORT_PHYSICAL.match(trimmed)
            if m:
                current_port = m.group(1)
                port_indent = indent
                in_ethernet = False
                continue
            # LAG
            m = RE_PORT_LAG.match(trimmed)
            if m:
                current_port = f'lag-{m.group(1)}'
                port_indent = indent
                in_ethernet = False
                continue
        else:
            if trimmed == 'exit' and indent == port_indent:
                current_port = ''
                port_indent = -1
                in_ethernet = False
                continue
            if trimmed == 'ethernet' and not in_ethernet:
                in_ethernet = True
                ethernet_indent = indent
                continue
            if in_ethernet and trimmed == 'exit' and indent == ethernet_indent:
                in_ethernet = False
                continue
            if not in_ethernet:
                m = RE_DESCRIPTION.match(trimmed)
                if m:
                    port_map[current_port] = m.group(1)

    return port_map


def parse_base_router_interfaces(config_text: str, port_desc_map: dict[str, str]) -> list[dict]:
    """
    Base Router(글로벌) 섹션의 인터페이스 IP 추출
    parserV3.ts의 들여쓰기 기반 블록 파싱 방식 참고
    """
    interfaces = []
    lines = config_text.split('\n')

    in_router = False
    router_indent = -1
    current_iface = None
    iface_indent = -1

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        indent = len(line) - len(line.lstrip())

        # router / router Base 섹션 진입 감지
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

        # interface 블록 시작 (router 섹션 1레벨 하위)
        if indent == router_indent + 4 and trimmed.startswith('interface "'):
            if current_iface:
                interfaces.append(current_iface)
            m = RE_IFACE_NAME.match(trimmed)
            if m:
                current_iface = {
                    'interface_name': m.group(1),
                    'ip': '',
                    'secondary_ips': [],
                    'port': '',
                    'interface_desc': '',
                    'admin_state': 'Shutdown',
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

        # address (primary)
        m = RE_ADDRESS.match(trimmed)
        if m:
            current_iface['ip'] = m.group(1)
            continue

        # secondary address — local_subnet_map 추론용으로만 수집 (IpRecord 미생성)
        m = RE_SECONDARY.match(trimmed)
        if m:
            current_iface['secondary_ips'].append(m.group(1))
            continue

        # port
        m = RE_PORT_REF.match(trimmed)
        if m:
            current_iface['port'] = m.group(1)
            continue

        # interface-level description
        m = RE_DESCRIPTION.match(trimmed)
        if m:
            current_iface['interface_desc'] = m.group(1)
            continue

        # admin state
        if trimmed == 'no shutdown':
            current_iface['admin_state'] = 'Active'
        elif trimmed == 'shutdown':
            current_iface['admin_state'] = 'Shutdown'

    # 포트 description 보강
    for iface in interfaces:
        port = iface.get('port', '')
        if port and port in port_desc_map:
            iface['port_desc'] = port_desc_map[port]
        else:
            iface['port_desc'] = ''

    return interfaces


def parse_ies_interfaces(config_text: str, port_desc_map: dict[str, str]) -> list[dict]:
    """
    service > ies 섹션의 인터페이스 IP 추출 (BB 장비 전용)
    Nokia 7750 SR IES(Internet Enhanced Service)에서 interface IP를 파싱.
    구조: service > ies {id} > interface "{name}" create > address / sap / description
    """
    interfaces = []
    lines = config_text.split('\n')

    in_service = False
    service_indent = -1
    in_ies = False
    ies_indent = -1
    current_iface = None
    iface_indent = -1

    for line in lines:
        raw = line.rstrip('\r\n')
        trimmed = raw.strip()
        if not trimmed:
            continue
        indent = len(raw) - len(raw.lstrip())

        # service 섹션 진입
        if not in_service and trimmed == 'service':
            in_service = True
            service_indent = indent
            continue

        if not in_service:
            continue

        # service 섹션 종료
        if trimmed == 'exit' and indent == service_indent:
            if current_iface:
                interfaces.append(current_iface)
                current_iface = None
            in_service = False
            in_ies = False
            continue

        # ies 블록 진입 (ies 10 name "10" customer 1 create 형태)
        if not in_ies and RE_IES_HEADER.match(trimmed) and indent == service_indent + 4:
            if current_iface:
                interfaces.append(current_iface)
                current_iface = None
            in_ies = True
            ies_indent = indent
            continue

        if not in_ies:
            continue

        # ies 블록 종료
        if trimmed == 'exit' and indent == ies_indent:
            if current_iface:
                interfaces.append(current_iface)
                current_iface = None
            in_ies = False
            continue

        # interface 블록 시작 (interface "name" create)
        if indent == ies_indent + 4 and RE_IES_IFACE.match(trimmed):
            if current_iface:
                interfaces.append(current_iface)
            m = RE_IES_IFACE.match(trimmed)
            current_iface = {
                'interface_name': m.group(1),
                'ip': '',
                'secondary_ips': [],
                'port': '',
                'interface_desc': '',
                'admin_state': 'Active',
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

        # address primary (indent == iface_indent + 4 수준)
        m = RE_ADDRESS.match(trimmed)
        if m:
            current_iface['ip'] = m.group(1)
            continue

        # secondary address — local_subnet_map 추론용으로만 수집 (IpRecord 미생성)
        m = RE_SECONDARY.match(trimmed)
        if m:
            current_iface['secondary_ips'].append(m.group(1))
            continue

        # SAP에서 포트 추출 (sap 1/2/6 create 또는 sap lag-1 create)
        m = RE_SAP_PORT.match(trimmed)
        if m:
            current_iface['port'] = m.group(1)
            continue

        # description
        m = RE_DESCRIPTION.match(trimmed)
        if m:
            current_iface['interface_desc'] = m.group(1)
            continue

        # admin state
        if trimmed == 'no shutdown':
            current_iface['admin_state'] = 'Active'
        elif trimmed == 'shutdown':
            current_iface['admin_state'] = 'Shutdown'

    # SAP 없는 인터페이스: 이름에서 포트 추론 (p3/1/10 → 3/1/10)
    _RE_IFACE_PORT = re.compile(r'^p(\d+/\d+/\d+(?:\.\d+)?)')
    for iface in interfaces:
        if not iface.get('port') and iface.get('interface_name'):
            m = _RE_IFACE_PORT.match(iface['interface_name'])
            if m:
                iface['port'] = m.group(1)

    # 포트 description 보강
    for iface in interfaces:
        port = iface.get('port', '')
        if port and port in port_desc_map:
            iface['port_desc'] = port_desc_map[port]
        else:
            iface['port_desc'] = ''

    return interfaces


def parse_static_routes(config_text: str) -> list[dict]:
    """
    Base Router Static Route 추출 (description, admin_state 포함)
    parserV3.ts RE_STATIC_ROUTE_ENTRY / RE_NEXT_HOP 참고
    """
    routes = []
    lines = config_text.split('\n')

    current_prefix = None
    prefix_indent = -1
    current_nh = None
    nh_indent = -1
    in_router = False
    router_indent = -1

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        indent = len(line) - len(line.lstrip())

        # router 섹션 내에서만 파싱
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

        # inline static-route (구버전): static-route X/Y next-hop A.B.C.D [description "..."]
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

        # static-route-entry (신버전 블록 형식)
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

        # static-route-entry 블록 종료
        if trimmed == 'exit' and indent == prefix_indent:
            if current_nh:
                routes.append(current_nh)
                current_nh = None
            current_prefix = None
            continue

        # next-hop
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

        # next-hop 블록 종료
        if trimmed == 'exit' and indent == nh_indent:
            routes.append(current_nh)
            current_nh = None
            continue

        # description
        m = RE_DESCRIPTION.match(trimmed)
        if m:
            current_nh['description'] = m.group(1)
            continue

        # shutdown
        if trimmed == 'shutdown':
            current_nh['admin_state'] = 'Shutdown'

    return routes


# ─────────────────────────────────────────────
# 전체 파싱 (파일 1개)
# ─────────────────────────────────────────────

def parse_config_file(filepath: str) -> list[IpRecord]:
    """단일 config 파일을 파싱하여 IpRecord 목록 반환"""
    path = Path(filepath)
    filename = path.name

    try:
        config_text = path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return []

    device = extract_device_info(config_text, filename)
    port_desc_map = extract_port_descriptions(config_text)
    base_ifaces = parse_base_router_interfaces(config_text, port_desc_map)
    ies_ifaces = parse_ies_interfaces(config_text, port_desc_map)
    static_routes = parse_static_routes(config_text)

    records: list[IpRecord] = []

    def make_base(ip_type: str, cidr: str) -> dict:
        """공통 필드 딕셔너리"""
        parts = cidr.split('/')
        ip = parts[0]
        prefix = int(parts[1]) if len(parts) == 2 else 32
        return dict(
            cidr=cidr,
            ip_address=ip,
            prefix_length=prefix,
            subnet_mask=prefix_to_mask(prefix),
            network_address=get_network_address(cidr),
            ip_type=ip_type,
            device_name=device['hostname'] or filename.rsplit(' ', 1)[0],
            device_model=device['model'],
            location=device['location'],
            os_version=device['os_version'],
            config_date=device['config_date'],
            router_id=device['router_id'],
            as_number=device['as_number'],
            filename=filename,
        )

    # 1. System IP
    if device['system_ip']:
        cidr = f"{device['system_ip']}/32"
        b = make_base('System IP', cidr)
        records.append(IpRecord(
            **b,
            interface_name='system',
            port='',
            interface_desc='',
            port_desc='',
            peer_device='',
            peer_port='',
            next_hop_ip='',
            route_desc='',
            admin_state='Active',
        ))

    # 2. Interface IP (router Base + IES 서비스)
    for iface in base_ifaces + ies_ifaces:
        if not iface['ip']:
            continue
        iface_name = iface['interface_name']
        if iface_name.lower() == 'system':
            continue  # System IP는 이미 처리

        # Peer 추출: interface description 우선, 없으면 port description
        peer_desc = iface.get('interface_desc') or iface.get('port_desc', '')
        peer_device, peer_port = extract_peer_from_desc(peer_desc)

        b = make_base('Interface IP', iface['ip'])
        records.append(IpRecord(
            **b,
            interface_name=iface_name,
            port=iface.get('port', ''),
            interface_desc=iface.get('interface_desc', ''),
            port_desc=iface.get('port_desc', ''),
            peer_device=peer_device,
            peer_port=peer_port,
            next_hop_ip='',
            route_desc='',
            admin_state=iface.get('admin_state', 'Active'),
        ))

    # ── 로컬 인터페이스 서브넷 맵 구성 ──
    # next-hop IP가 어느 로컬 인터페이스 서브넷에 속하는지 조회하여 출구 인터페이스 추론
    local_subnet_map: list[tuple] = []  # (IPv4Network, interface_name, port, iface_desc, port_desc)
    for _iface in base_ifaces + ies_ifaces:
        if not _iface.get('ip'):
            continue
        _iface_key = (
            _iface['interface_name'],
            _iface.get('port', ''),
            _iface.get('interface_desc', ''),
            _iface.get('port_desc', ''),
        )
        try:
            net = IPv4Network(_iface['ip'], strict=False)
            local_subnet_map.append((net, *_iface_key))
        except (AddressValueError, ValueError):
            pass
        # secondary address도 동일 인터페이스의 서브넷으로 등록 (next-hop 추론 전용)
        for sec_cidr in _iface.get('secondary_ips', []):
            try:
                sec_net = IPv4Network(sec_cidr, strict=False)
                local_subnet_map.append((sec_net, *_iface_key))
            except (AddressValueError, ValueError):
                pass

    def find_egress_iface(nh_ip: str):
        """next-hop IP로 출구 인터페이스 정보 반환 (interface_name, port, iface_desc, port_desc)"""
        if not nh_ip:
            return '', '', '', ''
        try:
            addr = IPv4Address(nh_ip)
            for net, iface_name, port, iface_desc, port_desc in local_subnet_map:
                # /31(RFC 3021 P2P)은 두 주소 모두 유효 호스트 → network_address 제외 불필요
                if addr in net and (net.prefixlen >= 31 or str(addr) != str(net.network_address)):
                    return iface_name, port, iface_desc, port_desc
        except (AddressValueError, ValueError):
            pass
        return '', '', '', ''

    # 3. Static Route
    for route in static_routes:
        b = make_base('Static Route', route['prefix'])
        peer_device, peer_port = extract_peer_from_desc(route.get('description', ''))
        egress_name, egress_port, egress_idesc, egress_pdesc = find_egress_iface(route['next_hop'])
        records.append(IpRecord(
            **b,
            interface_name=egress_name,
            port=egress_port,
            interface_desc=egress_idesc,
            port_desc=egress_pdesc,
            peer_device=peer_device,
            peer_port=peer_port,
            next_hop_ip=route['next_hop'],
            route_desc=route.get('description', ''),
            admin_state=route.get('admin_state', 'Active'),
        ))

    return records


# ─────────────────────────────────────────────
# 디렉토리 전체 파싱 + Next-hop 역방향 맵
# ─────────────────────────────────────────────

def parse_all_configs(config_dir: str) -> list[dict]:
    """
    지정 디렉토리의 모든 .txt config 파일을 파싱.
    1단계: 각 파일 파싱
    2단계: 동일 장비(hostname 기준) 중복 파일 → 최신 날짜 파일만 유지
    3단계: next-hop 역방향 맵 구축
    4단계: Static Route의 peer_device 자동 채우기
    """
    config_path = Path(config_dir)

    # 파일별 파싱
    file_records: dict[str, list[IpRecord]] = {}
    txt_files = sorted(config_path.glob('*.txt'))
    for f in txt_files:
        records = parse_config_file(str(f))
        if records:
            file_records[str(f)] = records

    # hostname 기준으로 최신 파일 선택
    # value: (config_date, filepath) — 날짜 동일 시 파일명 알파벳 내림차순으로 tie-break
    latest: dict[str, tuple[str, str]] = {}
    for filepath, records in file_records.items():
        hostname = records[0].device_name
        config_date = records[0].config_date or ''
        key = (config_date, filepath)
        if hostname not in latest or key > latest[hostname]:
            latest[hostname] = key

    # 최신 파일의 레코드만 수집
    latest_paths = {v[1] for v in latest.values()}
    all_records: list[IpRecord] = []
    for filepath in sorted(latest_paths):
        all_records.extend(file_records[filepath])

    # ── Next-hop 역방향 맵 구축 ──
    # { IP주소: {device_name, interface_name, cidr} }
    nexthop_map: dict[str, dict] = {}
    for rec in all_records:
        if rec.ip_type in ('System IP', 'Interface IP') and rec.ip_address:
            nexthop_map[rec.ip_address] = {
                'device_name': rec.device_name,
                'interface_name': rec.interface_name,
                'cidr': rec.cidr,
            }

    # ── Static Route peer_device 보강 ──
    for rec in all_records:
        if rec.ip_type == 'Static Route' and not rec.peer_device:
            hit = nexthop_map.get(rec.next_hop_ip)
            if hit:
                rec.peer_device = hit['device_name']
                rec.peer_port = hit['interface_name']

    return [_record_to_dict(r) for r in all_records]


def _record_to_dict(r: IpRecord) -> dict:
    return {
        'cidr':             r.cidr,
        'ip_address':       r.ip_address,
        'prefix_length':    r.prefix_length,
        'subnet_mask':      r.subnet_mask,
        'network_address':  r.network_address,
        'ip_type':          r.ip_type,
        'device_name':      r.device_name,
        'device_model':     r.device_model,
        'location':         r.location,
        'os_version':       r.os_version,
        'config_date':      r.config_date,
        'interface_name':   r.interface_name,
        'port':             r.port,
        'interface_desc':   r.interface_desc,
        'port_desc':        r.port_desc,
        'peer_device':      r.peer_device,
        'peer_port':        r.peer_port,
        'next_hop_ip':      r.next_hop_ip,
        'route_desc':       r.route_desc,
        'admin_state':      r.admin_state,
        'router_id':        r.router_id,
        'as_number':        r.as_number,
        'filename':         r.filename,
    }
