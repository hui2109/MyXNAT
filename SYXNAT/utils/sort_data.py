import re
from collections import OrderedDict
from pathlib import Path
from shutil import copy2

import pydicom


def process_data(data_type: str, dcm_file, dcm, data_dict, study_dict):
    StudyInstanceUID = dcm.StudyInstanceUID
    SeriesInstanceUID = dcm.SeriesInstanceUID
    study_dict[StudyInstanceUID] = 0

    if data_type not in data_dict:
        data_dict[data_type] = {}
        data_dict[data_type][StudyInstanceUID] = {}
        data_dict[data_type][StudyInstanceUID][SeriesInstanceUID] = [dcm_file]
    else:
        if StudyInstanceUID not in data_dict[data_type]:
            data_dict[data_type][StudyInstanceUID] = {}
            data_dict[data_type][StudyInstanceUID][SeriesInstanceUID] = [dcm_file]
        else:
            if SeriesInstanceUID not in data_dict[data_type][StudyInstanceUID]:
                data_dict[data_type][StudyInstanceUID][SeriesInstanceUID] = [dcm_file]
            else:
                data_dict[data_type][StudyInstanceUID][SeriesInstanceUID].append(dcm_file)


class DicomSorter:
    def __init__(self, root_path: str, sorted_path: str):
        self.root_path = Path(root_path)
        self.sorted_path = Path(sorted_path)
        self.pattern1 = re.compile(r'^([A-Z]+)\.[0-9]')
        self.data_sort_dict = OrderedDict()
        self.study_id_dict = OrderedDict()

        # MOdality: ['CT', 'MR', 'MP', 'MW', 'RD', 'RE', 'RI', 'RP', 'RS', 'RT']

    def __get_order_by_modality(self):
        for patient_dir in self.root_path.iterdir():
            dcm_files = sorted(patient_dir.glob('**/*.dcm'), key=lambda x: x.name)
            data_dict = OrderedDict()
            study_dict = OrderedDict()

            for dcm_file in dcm_files:
                dcm = pydicom.dcmread(dcm_file)
                res = self.pattern1.search(dcm_file.name).group(1)

                if res == 'CT':  # CT_CT
                    process_data('CT_CT', dcm_file, dcm, data_dict, study_dict)
                elif res == 'MR':  # MR_MR
                    process_data('MR_MR', dcm_file, dcm, data_dict, study_dict)
                elif res == 'MP':  # MP_MOTIONMTPROTOCOL
                    process_data('MP_MOTIONMTPROTOCOL', dcm_file, dcm, data_dict, study_dict)
                elif res == 'MW':  # MW_MOTIONMTWAVEFORM
                    process_data('MW_MOTIONMTWAVEFORM', dcm_file, dcm, data_dict, study_dict)
                elif res == 'RD':  # RD_RTDOSE
                    process_data('RD_RTDOSE', dcm_file, dcm, data_dict, study_dict)
                elif res == 'RE':  # RE_REG
                    process_data('RE_REG', dcm_file, dcm, data_dict, study_dict)
                elif res == 'RI':  # RI_RTIMAGE
                    process_data('RI_RTIMAGE', dcm_file, dcm, data_dict, study_dict)
                elif res == 'RP':  # RP_RTPLAN
                    process_data('RP_RTPLAN', dcm_file, dcm, data_dict, study_dict)
                elif res == 'RS':  # RS_RTSTRUCT
                    process_data('RS_RTSTRUCT', dcm_file, dcm, data_dict, study_dict)
                elif res == 'RT':  # RT_RTRECORD
                    process_data('RT_RTRECORD', dcm_file, dcm, data_dict, study_dict)
                else:
                    print(res)

            self.data_sort_dict[patient_dir.name] = data_dict
            self.study_id_dict[patient_dir.name] = study_dict

    def copy_files(self):
        self.__get_order_by_modality()

        for patient_dir, data_dict in self.data_sort_dict.items():
            study_id_list = list(self.study_id_dict[patient_dir].keys())

            for data_type, study_id_dict in data_dict.items():
                for study_id, series_id_dict in study_id_dict.items():
                    for idx, (series_id, file_list) in enumerate(series_id_dict.items()):
                        for file in file_list:
                            dest_dir = self.sorted_path / patient_dir / data_type / f'Study{study_id_list.index(study_id) + 1}_{study_id}' / f'Series{idx + 1}_{series_id}'
                            dest_dir.mkdir(parents=True, exist_ok=True)
                            copy2(file, dest_dir)


if __name__ == '__main__':
    ds = DicomSorter('/Users/kukudehui/Desktop/XNAT_DATA/patient_data', '/Users/kukudehui/Desktop/XNAT_DATA/sorted_data')
    ds.copy_files()
