from requests import Session

from .CONFIG import URL, USER, PASSWORD, Default_DCMFIELD, Default_DATE


def get_session():
    session = Session()
    session.post(f"{URL}/data/JSESSION", auth=(USER, PASSWORD))
    return session


def get_dcm_field(dcm_file, tag: str, default: str = Default_DCMFIELD):
    """类型安全地读取 DICOM 字段，缺失或为空时返回 default。"""
    try:
        val = getattr(dcm_file, tag)
        # pydicom 的空序列 / None / 空字符串均视为无值
        if val is None or str(val).strip() == '':
            return default
        return str(val)
    except AttributeError:
        return default


def fmt_date(raw, default: str = Default_DATE):
    """将 YYYYMMDD 格式转为 YYYY-MM-DD，原始值已是默认占位符时直接返回。"""
    s = str(raw)
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return default
