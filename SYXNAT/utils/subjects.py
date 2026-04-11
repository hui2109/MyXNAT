from requests import Session

from .CONFIG import URL
from .interfaces import MySubject, Gender, Handedness


def create_subject(session: Session, projectID: str, my_subject: MySubject):
    if my_subject.label == '':
        raise ValueError('Subject label cannot be empty!')

    url = f'{URL}/data/projects/{projectID}/subjects/{my_subject.label}'
    subject_params = my_subject.model_dump(mode='json', exclude_unset=True, exclude={'label', 'name', 'identity'})
    subject_params.update({
        "xnat:subjectData/fields/field[name=name]/field": my_subject.name,
        "xnat:subjectData/fields/field[name=identity]/field": my_subject.identity,
    })

    response = session.put(url=url, params=subject_params)
    return response.status_code, response.text


def delete_subject(session: Session, projectID: str, subjectLabel: str):
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}'
    response = session.delete(url=url)
    return response.status_code, response.text


def get_subject(session: Session, projectID: str, subjectLabel: str) -> MySubject:
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}'
    response = session.get(url=url, params={'format': 'json'})
    result = response.json()

    # ── 顶层 item ──────────────────────────────────────────────
    item = result['items'][0]
    data_fields: dict = item.get('data_fields', {})
    children: list = item.get('children', [])

    # ── 从 children 中分类提取子节点 ─────────────────────────────
    demographics: dict = {}
    custom_fields: dict = {}

    for child in children:
        field_name = child.get('field', '')
        child_items = child.get('items', [])

        if field_name == 'demographics' and child_items:
            demographics = child_items[0].get('data_fields', {})
        elif field_name == 'fields/field':
            for cf in child_items:
                cf_data = cf.get('data_fields', {})
                key = cf_data.get('name', '')  # e.g. 'name' / 'identity'
                value = cf_data.get('field', '')  # 对应的值
                if key:
                    custom_fields[key] = value

    # ── Gender / Handedness 安全映射 ───────────────────────────
    def parse_gender(raw: str | None) -> Gender:
        if raw is None:
            return None
        return Gender(raw.lower())

    def parse_handedness(raw: str | None) -> Handedness:
        if raw is None:
            return None
        return Handedness(raw.lower())

    # ── 组装 MySubject ────────────────────────────────────────
    return MySubject(
        # 基本信息
        label=data_fields.get('label', ''),
        group=data_fields.get('group', ''),
        src=data_fields.get('src', ''),
        # 人口统计
        dob=demographics.get('dob', ''),
        gender=parse_gender(demographics.get('gender', None)),
        handedness=parse_handedness(demographics.get('handedness', None)),
        education=str(demographics.get('education', '')),
        race=demographics.get('race', ''),
        ethnicity=demographics.get('ethnicity', ''),
        height=str(demographics.get('height', '')),
        weight=str(demographics.get('weight', '')),
        # 自定义字段
        name=custom_fields.get('name', ''),
        identity=custom_fields.get('identity', ''),
    )


def update_subject(session: Session, projectID: str, subjectLabel: str, my_subject: MySubject):
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}'
    subject_params = my_subject.model_dump(mode='json', exclude_unset=True, exclude={'label', 'name', 'identity'})
    subject_params.update({
        "xnat:subjectData/fields/field[name=name]/field": my_subject.name,
        "xnat:subjectData/fields/field[name=identity]/field": my_subject.identity,
    })

    response = session.put(url=url, params=subject_params)
    return response.status_code, response.text
