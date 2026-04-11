from collections import OrderedDict
from pathlib import Path

from pydicom import dcmread
from requests import Session

from ..utils.CONFIG import Default_DCMFIELD
from ..utils.interfaces import Modality, MySubject, MyExperiment, MyScan, Gender, ExperimentType, ScanType, ScanQuality
from ..utils.utils import get_dcm_field, fmt_date
from functools import partial


class UploadSubjects:
    def __init__(self, session: Session, projectID: str, parent_dir: str):
        self.session = session
        self.projectID = projectID
        self.parent_P = Path(parent_dir)
        self.project_data = OrderedDict()

    def __judge_CBCT(self, dcm_file):
        model_name = get_dcm_field(dcm_file, 'ManufacturerModelName').lower()
        if self.modality.name == 'CT' and ('cone-beam ct' in model_name or 'verification' in model_name):
            self.modality = Modality.CBCT

    def __parse_fields(self, dcm_file):
        # 先判断这个文件的 modality 是不是 CBCT
        self.__judge_CBCT(dcm_file)

        # ── Subject Fields ──────────────────────────────────────────
        if self.my_subject.label == '':
            self.my_subject.label = get_dcm_field(dcm_file, 'PatientID')

        if self.my_subject.dob == '':
            self.my_subject.dob = fmt_date(get_dcm_field(dcm_file, 'PatientBirthDate'))

        if self.my_subject.gender is None:
            sex = get_dcm_field(dcm_file, 'PatientSex')
            if sex == 'M':
                self.my_subject.gender = Gender.male
            elif sex == 'F':
                self.my_subject.gender = Gender.female
            else:
                self.my_subject.gender = Gender.unknown

        if self.my_subject.name == '':
            patient_name = get_dcm_field(dcm_file, 'PatientName')
            if patient_name == Default_DCMFIELD:
                self.my_subject.name = Default_DCMFIELD
            else:
                self.my_subject.name = dcm_file.PatientName.family_name + '_' + dcm_file.PatientName.given_name

        if self.my_subject.identity == '':
            self.my_subject.identity = get_dcm_field(dcm_file, 'OtherPatientIDs')

        # ── Experiment Fields ────────────────────────────────────────
        if self.my_experiment.label == '':
            self.my_experiment.label = f"{self.study}_{self.idx}"

        if self.my_experiment.xsiType is None:
            self.my_experiment.xsiType = ExperimentType.RTSession

        if self.my_experiment.date == '':
            self.my_experiment.date = fmt_date(get_dcm_field(dcm_file, 'StudyDate'))

        if self.my_experiment.operator == '':
            # PhysiciansOfRecord 是 PersonName 对象，必须先 str() 再 replace
            raw = get_dcm_field(dcm_file, 'PhysiciansOfRecord')
            self.my_experiment.operator = raw.replace('^', '').replace('$', '')

        if self.my_experiment.studyid == '':
            self.my_experiment.studyid = get_dcm_field(dcm_file, 'StudyInstanceUID')

        if self.modality.value not in self.my_experiment.modalities:
            self.my_experiment.modalities.append(self.modality.value)

        # ── Scan Fields ──────────────────────────────────────────────
        if self.my_scan.id == '':
            self.my_scan.id = f"{self.modality.name}_{self.series_idx}_{self.frames}"

        if self.my_scan.type == '':
            self.my_scan.type = self.modality.name

        if self.my_scan.xsiType is None:
            self.my_scan.xsiType = ScanType.RTScan

        if self.my_scan.quality is None:
            self.my_scan.quality = ScanQuality.usable

        if self.my_scan.scanner == '':
            manufacturer = get_dcm_field(dcm_file, 'Manufacturer')
            model_name = get_dcm_field(dcm_file, 'ManufacturerModelName')
            station_name = get_dcm_field(dcm_file, 'StationName')
            self.my_scan.scanner = f"{manufacturer}_{model_name}_{station_name}"

        if self.my_scan.condition == '':
            # OperatorsName 同样是 PersonName 对象
            raw = get_dcm_field(dcm_file, 'OperatorsName')
            self.my_scan.condition = raw.replace('^', '').replace('$', '')

        if self.my_scan.series_description == '':
            self.my_scan.series_description = get_dcm_field(dcm_file, 'SeriesInstanceUID')

        if self.my_scan.note == '':
            study_desc = get_dcm_field(dcm_file, 'StudyDescription')
            series_desc = get_dcm_field(dcm_file, 'SeriesDescription')
            self.my_scan.note = f"{study_desc}___{series_desc}"

        if self.my_scan.frames == '':
            self.my_scan.frames = self.frames

    def _sort_by_subject(self):
        subject_list = []
        for subject_dir in sorted(self.parent_P.iterdir(), key=lambda x: x.name):
            if not subject_dir.is_dir():
                continue

            self.my_subject = MySubject()

            experiment_list = []
            for study_dir in sorted(subject_dir.iterdir(), key=lambda x: x.name):
                if not study_dir.is_dir():
                    continue

                self.my_experiment = MyExperiment()
                self.study, self.idx, study_id = study_dir.name.split('_')

                modality_list = []
                for modality_dir in sorted(study_dir.iterdir(), key=lambda x: x.name):
                    if not modality_dir.is_dir():
                        continue

                    current_modality = Modality(modality_dir.name.split('_')[-1])
                    self.modality = Modality(current_modality.value)

                    scan_list = []
                    for series_dir in sorted(modality_dir.iterdir(), key=lambda x: x.name):
                        if not series_dir.is_dir():
                            continue

                        self.my_scan = MyScan()
                        self.series_idx, self.frames = series_dir.name.split('_')

                        file_list = []
                        for file in sorted(series_dir.iterdir(), key=lambda x: x.name):
                            if 'DS_Store' in file.name:
                                continue

                            dcm_file = dcmread(file)
                            self.__parse_fields(dcm_file)
                            file_list.append(file)

                        # 把modality复原
                        self.modality = Modality(current_modality.value)
                        scan_list.append(OrderedDict({self.my_scan: file_list}))
                    modality_list += scan_list
                experiment_list.append(OrderedDict({self.my_experiment: modality_list}))
            subject_list.append(OrderedDict({self.my_subject: experiment_list}))

        return subject_list

    def __create_subjects_recursively(self):
        pass

    def __upload_files_sequentially(self):
        pass

    def upload_subjects(self):
        # 先整理数据
        subject_list = self._sort_by_subject()
        self.project_data = OrderedDict({self.projectID: subject_list})

        # 然后依次新建
        self.__create_subjects_recursively()

        # 最后批量上传
        self.__upload_files_sequentially()
