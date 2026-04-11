from enum import Enum

from pydantic import BaseModel


class Gender(Enum):
    male = 'male'
    female = 'female'
    unknown = 'unknown'


class Handedness(Enum):
    right = 'right'
    left = 'left'
    ambidextrous = 'ambidextrous'
    unknown = 'unknown'


class ExperimentType(Enum):
    CTSession = 'xnat:crSessionData'
    MRSession = 'xnat:mrSessionData'
    RTSession = 'xnat:rtSessionData'


class ScanType(Enum):
    CTScan = 'xnat:ctScanData'
    MRScan = 'xnat:mrScanData'
    RTScan = 'xnat:rtImageScanData'


class ScanQuality(Enum):
    usable = 'usable'
    questionable = 'questionable'
    unusable = 'unusable'


# 患者字段类
class MySubject(BaseModel):
    label: str = ''  # ID
    dob: str = ''  # 出生日期 '1990-05-15'
    gender: Gender | None = None  # 性别
    # 自定义字段
    name: str = ''  # 患者姓名 'zhang san_张三'
    identity: str = ''  # 患者身份证 '510000000000000000'

    # 待定字段
    group: str = ''  # 组别 待定
    handedness: Handedness | None = None  # 惯用手 待定
    education: str = ''  # 受教育年限 待定
    race: str = ''  # 种族 待定
    ethnicity: str = ''  # 民族 'han' 待定
    height: str = ''  # 身高 待定
    weight: str = ''  # 体重 待定
    src: str = ''  # 招募类型 'Online Advertisement' 待定

    # 备选字段
    # yob: str = ''  # Year of Birth (与 dob 二选一) '1990' 备选字段
    # age: str = ''  # Age (与 dob 二选一) '34' 备选字段

    def __hash__(self):
        return hash(self.label)  # id 字段已保证唯一性

    def __eq__(self, other):
        if isinstance(other, MySubject):
            return self.label == other.label
        return False


# Study字段类
class MyExperiment(BaseModel):
    label: str = ''  # 序号 study_1_subjectLabel
    xsiType: ExperimentType | None = None  # 类型 默认均为 ExperimentType.RTSession
    date: str = ''  # 日期 '2023-05-15'
    note: str = ''  # 备注
    operator: str = ''  # 主管医师 'wang ying'
    # 自定义字段
    studyid: str = ''  # Study Instance UID
    modalities: list[str] = []  # 成像类型 ['CT', 'CBCT', 'RP']

    # 待定字段
    visit_id: str = ''  # 访问ID 待定
    scanner: str = ''  # 扫描机器 待定
    acquisition_site: str = ''  # 采集地点 待定

    def __hash__(self):
        return hash(self.studyid)  # studyid 字段已保证唯一性

    def __eq__(self, other):
        if isinstance(other, MyExperiment):
            return self.label == other.label
        return False


# Series字段类
class MyScan(BaseModel):
    id: str = ''  # 序列ID 'CT_Series1_64' CT成像类型_序列ID_帧数
    type: str = ''  # 成像类型 'CBCT'
    xsiType: ScanType | None = None  # 类型 默认均为 ScanType.RTScan
    quality: ScanQuality | None = None  # 扫描质量 默认为 ScanQuality.usable
    scanner: str = ''  # 扫描机器 'SIEMENS_SOMATOM Definition AS_CTAWP95526' Manufacturer_Manufacturer’s Model Name_Station Name
    condition: str = ''  # 操作者(即采集这个Series的人的名字) 'yanyy'
    note: str = ''  # Series Instance UID
    series_description: str = ''  # 备注 Study Description___Series Description
    frames: str = ''  # 帧数

    # 待定字段
    documentation: str = ''
    modality: str = ''

    def __hash__(self):
        return hash(self.note)  # note 字段已保证唯一性

    def __eq__(self, other):
        if isinstance(other, MyScan):
            return self.id == other.id
        return False


class Modality(Enum):
    CT = 'CT'
    CBCT = 'CBCT'
    MR = 'MR'
    MP = 'MOTIONMTPROTOCOL'
    MW = 'MOTIONMTWAVEFORM'
    RD = 'RTDOSE'
    RE = 'REG'
    RI = 'RTIMAGE'
    RP = 'RTPLAN'
    RS = 'RTSTRUCT'
    RT = 'RTRECORD'
