import re
from collections import OrderedDict
from pathlib import Path
from shutil import copy2

import pydicom


class DicomSorter:
    def __init__(self, root_path: str, sorted_path: str):
        self.root_path = Path(root_path)
        self.sorted_path = Path(sorted_path)
        self.pattern1 = re.compile(r'^([A-Z]+)\.[0-9]')
        self.data_sort_dict = OrderedDict()
        # MOdality: ['CT', 'MR', 'MP', 'MW', 'RD', 'RE', 'RI', 'RP', 'RS', 'RT']

    def __process_data(self, data_type: str, dcm_file: Path):
        if data_type not in self.modality_dict:
            self.modality_dict[data_type] = OrderedDict()
            self.modality_dict[data_type][self.SeriesInstanceUID] = [dcm_file]
        else:
            if self.SeriesInstanceUID not in self.modality_dict[data_type]:
                self.modality_dict[data_type][self.SeriesInstanceUID] = [dcm_file]
            else:
                self.modality_dict[data_type][self.SeriesInstanceUID].append(dcm_file)

    def __get_order_by_studyID(self):
        for patient_dir in self.root_path.iterdir():
            dcm_files = sorted(patient_dir.glob('**/*.dcm'), key=lambda x: x.name)
            self.data_sort_dict[patient_dir.name] = OrderedDict()

            for dcm_file in dcm_files:
                dcm = pydicom.dcmread(dcm_file)
                res = self.pattern1.search(dcm_file.name).group(1)

                StudyInstanceUID = dcm.StudyInstanceUID
                self.SeriesInstanceUID = dcm.SeriesInstanceUID

                if StudyInstanceUID not in self.data_sort_dict[patient_dir.name]:
                    self.data_sort_dict[patient_dir.name][StudyInstanceUID] = OrderedDict()
                self.modality_dict = self.data_sort_dict[patient_dir.name][StudyInstanceUID]

                if res == 'CT':  # CT_CT
                    self.__process_data('CT_CT', dcm_file)
                elif res == 'MR':  # MR_MR
                    self.__process_data('MR_MR', dcm_file)
                elif res == 'MP':  # MP_MOTIONMTPROTOCOL
                    self.__process_data('MP_MOTIONMTPROTOCOL', dcm_file)
                elif res == 'MW':  # MW_MOTIONMTWAVEFORM
                    self.__process_data('MW_MOTIONMTWAVEFORM', dcm_file)
                elif res == 'RD':  # RD_RTDOSE
                    self.__process_data('RD_RTDOSE', dcm_file)
                elif res == 'RE':  # RE_REG
                    self.__process_data('RE_REG', dcm_file)
                elif res == 'RI':  # RI_RTIMAGE
                    self.__process_data('RI_RTIMAGE', dcm_file),
                elif res == 'RP':  # RP_RTPLAN
                    self.__process_data('RP_RTPLAN', dcm_file)
                elif res == 'RS':  # RS_RTSTRUCT
                    self.__process_data('RS_RTSTRUCT', dcm_file)
                elif res == 'RT':  # RT_RTRECORD
                    self.__process_data('RT_RTRECORD', dcm_file)
                else:
                    print(res)

    def copy_files(self):
        self.__get_order_by_studyID()

        for patient_dir, study_dict in self.data_sort_dict.items():
            study_id_list = list(study_dict.keys())

            for study_id, modality_dict in study_dict.items():
                for modality, series_dict in modality_dict.items():
                    for idx, (series_id, file_list) in enumerate(series_dict.items()):
                        file_num = len(file_list)

                        for file in file_list:
                            dest_dir = self.sorted_path / patient_dir / f'study_{study_id_list.index(study_id) + 1}_{study_id}' / modality / f'Series{idx + 1}_{file_num}'
                            dest_dir.mkdir(parents=True, exist_ok=True)
                            copy2(file, dest_dir)


if __name__ == '__main__':
    ds = DicomSorter('/Users/kukudehui/Desktop/XNAT_DATA/patient_data', '/Users/kukudehui/Desktop/XNAT_DATA/sorted_data')
    ds.copy_files()
