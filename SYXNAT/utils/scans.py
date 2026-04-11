from requests import Session

from .CONFIG import URL
from .interfaces import MyScan, ScanType, ScanQuality


def create_scan(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, my_scan: MyScan):
    if my_scan.id == '':
        raise ValueError('Scan id cannot be empty!')

    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}/scans/{my_scan.id}'
    scan_params = my_scan.model_dump(mode='json', exclude_unset=True, exclude={'id'})

    response = session.put(url=url, params=scan_params)
    return response.status_code, response.text


def delete_scan(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, scanID: str):
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}/scans/{scanID}'
    response = session.delete(url=url)
    return response.status_code, response.text


def get_scan(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, scanID: str):
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}/scans/{scanID}'
    response = session.get(url=url, params={'format': 'json'})
    result = response.json()

    item = result['items'][0]
    data_fields: dict = item.get('data_fields', {})

    def parse_scanType(raw: str | None):
        if raw is None:
            return None
        return ScanType(raw)

    def parse_scanQuality(raw: str | None):
        if raw is None:
            return None
        return ScanQuality(raw)

    return MyScan(
        id=data_fields.get('ID', ''),
        xsiType=parse_scanType(item['meta'].get('xsi:type', None)),
        type=data_fields.get('type', ''),
        series_description=data_fields.get('series_description', ''),
        quality=parse_scanQuality(data_fields.get('quality', None)),
        note=data_fields.get('note', ''),
        condition=data_fields.get('condition', ''),
        documentation=data_fields.get('documentation', ''),
        scanner=data_fields.get('scanner', ''),
        modality=data_fields.get('modality', ''),
        frames=str(data_fields.get('frames', '')),
    )


def update_scan(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, scanID: str, my_scan: MyScan):
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}/scans/{scanID}'
    scan_params = my_scan.model_dump(mode='json', exclude_unset=True, exclude={'id'})

    response = session.put(url=url, params=scan_params)
    return response.status_code, response.text
