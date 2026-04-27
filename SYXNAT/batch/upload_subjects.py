from collections import OrderedDict
from functools import partial
from pathlib import Path

from pydicom import dcmread
from requests import Session, HTTPError

from ..utils.CONFIG import Default_DCMFIELD
from ..utils.experiments import create_experiment
from ..utils.interfaces import Modality, MySubject, MyExperiment, MyScan, Gender, ExperimentType, ScanType, ScanQuality
from ..utils.resources import upload_resources
from ..utils.scans import create_scan
from ..utils.subjects import create_subject
from ..utils.utils import get_dcm_field, fmt_date


class UploadSubjects:
    def __init__(self, session: Session, projectID: str, parent_dir: str):
        self.session = session
        self.projectID = projectID
        self.parent_P = Path(parent_dir)
        self.project_data = OrderedDict({self.projectID: None})
        self.project_tasks = OrderedDict({
            self.projectID: OrderedDict(
                {
                    'subjects': [],
                    'experiments': [],
                    'scans': [],
                    'resources': [],
                }
            )
        })

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
            self.my_experiment.label = f"{self.study}_{self.idx}_{self.my_subject.label}"

        if self.my_experiment.xsiType is None:
            self.my_experiment.xsiType = ExperimentType.CTSession

        if self.my_experiment.date == '':
            self.my_experiment.date = fmt_date(get_dcm_field(dcm_file, 'StudyDate'))

        if self.my_experiment.operator == '':
            # PhysiciansOfRecord 是 PersonName 对象，必须先 str() 再 replace
            raw = get_dcm_field(dcm_file, 'PhysiciansOfRecord')
            self.my_experiment.operator = raw.replace('^', ' ').replace('$', ' ')

        if self.my_experiment.studyid == '':
            self.my_experiment.studyid = get_dcm_field(dcm_file, 'StudyInstanceUID')

        if self.modality.value not in self.my_experiment.modalities:
            self.my_experiment.modalities.append(self.modality.value)

        if self.my_experiment.UID == '':
            self.my_experiment.UID = self.my_experiment.studyid

        # ── Scan Fields ──────────────────────────────────────────────
        if self.my_scan.id == '':
            self.my_scan.id = f"{self.modality.name}_{self.series_idx}_{self.frames}"

        if self.my_scan.type == '':
            self.my_scan.type = self.modality.name

        if self.my_scan.xsiType is None:
            self.my_scan.xsiType = ScanType.CTScan

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
            self.my_scan.condition = raw.replace('^', ' ').replace('$', ' ')

        if self.my_scan.series_description == '':
            study_desc = get_dcm_field(dcm_file, 'StudyDescription')
            series_desc = get_dcm_field(dcm_file, 'SeriesDescription')
            self.my_scan.series_description = f"{study_desc}___{series_desc}"

        if self.my_scan.note == '':
            self.my_scan.note = get_dcm_field(dcm_file, 'SeriesInstanceUID')

        if self.my_scan.frames == '':
            self.my_scan.frames = self.frames

        if self.my_scan.UID == '':
            self.my_scan.UID = self.my_scan.note

        if self.my_scan.modality == '':
            self.my_scan.modality = self.current_modality.name  # 使用最原始的modality

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

                    self.current_modality = Modality(modality_dir.name.split('_')[-1])
                    self.modality = Modality(self.current_modality.value)

                    scan_list = []
                    for series_dir in sorted(modality_dir.iterdir(), key=lambda x: x.name):
                        if not series_dir.is_dir():
                            continue

                        self.my_scan = MyScan()
                        self.series_idx, self.frames = series_dir.name.split('_')

                        # file_list = []
                        for file in sorted(series_dir.iterdir(), key=lambda x: x.name):
                            if 'DS_Store' in file.name:
                                continue

                            dcm_file = dcmread(file)
                            self.__parse_fields(dcm_file)
                            # file_list.append(file)

                        # 把modality复原
                        self.modality = Modality(self.current_modality.value)
                        scan_list.append(OrderedDict({self.my_scan: series_dir}))
                    modality_list += scan_list
                experiment_list.append(OrderedDict({self.my_experiment: modality_list}))
            subject_list.append(OrderedDict({self.my_subject: experiment_list}))

        return subject_list

    def __create_tasks_recursively(self):
        for project_id, subject_list in self.project_data.items():
            for subject_dict in subject_list:
                for my_subject, experiment_list in subject_dict.items():
                    for experiment_dict in experiment_list:
                        for my_experiment, scan_list in experiment_dict.items():
                            for scan_dict in scan_list:
                                for my_scan, series_dir in scan_dict.items():
                                    self.project_tasks[self.projectID]['resources'].append(
                                        partial(upload_resources, self.session, project_id, my_subject.label, my_experiment.label, my_scan.id, series_dir))
                                    self.project_tasks[self.projectID]['scans'].append(
                                        partial(create_scan, self.session, project_id, my_subject.label, my_experiment.label, my_scan))
                            self.project_tasks[self.projectID]['experiments'].append(
                                partial(create_experiment, self.session, project_id, my_subject.label, my_experiment))
                    self.project_tasks[self.projectID]['subjects'].append(
                        partial(create_subject, self.session, project_id, my_subject))

    def __try_resource_task(self):
        try:
            failed_list = self.resource_task()
            return failed_list
        except Exception as e:
            print(f"[ERROR] [Resource] {e} 再次尝试......")
            self.__try_resource_task()

    def creat_tasks(self):
        # 先整理数据
        subject_list = self._sort_by_subject()
        self.project_data[self.projectID] = subject_list

        # 然后依次新建task
        self.__create_tasks_recursively()

    def handle_tasks_sequentially(self, *, subjects=True, experiments=True, scans=True, resources=True, recover_index=0):
        if subjects:
            for subject_task in self.project_tasks[self.projectID]['subjects']:
                status_code, text = subject_task()
                if status_code not in (200, 201):
                    print(f"[ERROR] [Subject] {subject_task=} {status_code=} {text=}")
                    raise HTTPError()
                else:
                    print(f"[SUCCESS] [Subject] {subject_task.args[-1].label}")

        if experiments:
            for experiment_task in self.project_tasks[self.projectID]['experiments']:
                status_code, text = experiment_task()
                if status_code not in (200, 201):
                    print(f"[ERROR] [Experiment] {experiment_task=} {status_code=} {text=}")
                    raise HTTPError()
                else:
                    print(f"[SUCCESS] [Experiment] {experiment_task.args[-2]} {experiment_task.args[-1].label}")

        if scans:
            for scan_task in self.project_tasks[self.projectID]['scans']:
                status_code, text = scan_task()
                if status_code not in (200, 201):
                    print(f"[ERROR] [Scan] {scan_task=} {status_code=} {text=}")
                    raise HTTPError()
                else:
                    print(f"[SUCCESS] [Scan] {scan_task.args[-3]} {scan_task.args[-2]} {scan_task.args[-1].id}")

        if resources:
            retry_times = 5
            for idx, resource_task in enumerate(self.project_tasks[self.projectID]['resources']):
                if idx < recover_index:
                    continue

                print(f"\033[31m[INFO] [Resources] {idx=} {resource_task.args[-4]} {resource_task.args[-3]} {resource_task.args[-2]} {resource_task.args[-1].absolute()}\033[0m")
                self.resource_task = resource_task
                failed_list = self.__try_resource_task()
                if failed_list:
                    failed_flag = True
                    # 有时候上传就是要抽风, 多试几次即可
                    for i in range(retry_times):
                        print(f'\033[31m[INFO] [Resources] {idx=} 上传失败, 重试第 {i} 次......\033[0m')
                        failed_list = self.__try_resource_task()
                        if not failed_list:
                            failed_flag = False
                            print(f"[SUCCESS] [Resources] {idx=} {resource_task.args[-4]} {resource_task.args[-3]} {resource_task.args[-2]} {resource_task.args[-1].absolute()}")
                            break
                    if failed_flag:
                        print(f"\033[31m[ERROR] [Resources] {idx=} {resource_task.args[-4]} {resource_task.args[-3]} {resource_task.args[-2]} {resource_task.args[-1].absolute()}\033[0m")
                        raise HTTPError()
                else:
                    print(f"[SUCCESS] [Resources] {idx=} {resource_task.args[-4]} {resource_task.args[-3]} {resource_task.args[-2]} {resource_task.args[-1].absolute()}")
