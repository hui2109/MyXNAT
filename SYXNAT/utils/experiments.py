from requests import Session

from .CONFIG import URL
from .interfaces import ExperimentType, MyExperiment


def create_experiment(session: Session, projectID: str, subjectLabel: str, my_experiment: MyExperiment):
    if my_experiment.label == '':
        raise ValueError('Experiment label cannot be empty!')

    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{my_experiment.label}'
    experiment_params = my_experiment.model_dump(mode='json', exclude_unset=True, exclude={'label', 'studyid', 'modalities', 'acquisition_site'})
    experiment_params.update({
        f"{my_experiment.xsiType.value}/fields/field[name=studyid]/field": my_experiment.studyid,
        f"{my_experiment.xsiType.value}/fields/field[name=modalities]/field": '_'.join(my_experiment.modalities),
        f"{my_experiment.xsiType.value}/acquisition_site": my_experiment.acquisition_site,
    })

    response = session.put(url=url, params=experiment_params)
    return response.status_code, response.text


def delete_experiment(session: Session, projectID: str, subjectLabel: str, experimentLabel: str):
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}'
    response = session.delete(url=url)
    return response.status_code, response.text


def get_experiment(session: Session, projectID: str, subjectLabel: str, experimentLabel: str):
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}'
    response = session.get(url=url, params={'format': 'json'})
    result = response.json()

    item = result['items'][0]
    data_fields: dict = item.get('data_fields', {})
    children: list = item.get('children', [])
    custom_fields: dict = {}

    for child in children:
        field_name = child.get('field', '')
        child_items = child.get('items', [])

        if field_name == 'fields/field':
            for cf in child_items:
                cf_data = cf.get('data_fields', {})
                key = cf_data.get('name', '')
                value = cf_data.get('field', '')
                if key:
                    custom_fields[key] = value

    def parse_experimentType(raw: str | None):
        if raw is None:
            return None
        return ExperimentType(raw)

    return MyExperiment(
        label=data_fields.get('label', ''),
        xsiType=parse_experimentType(item['meta'].get('xsi:type', None)),
        date=data_fields.get('date', ''),
        visit_id=data_fields.get('visit_id', ''),
        scanner=data_fields.get('scanner', ''),
        operator=data_fields.get('operator', ''),
        acquisition_site=data_fields.get('acquisition_site', ''),
        # 自定义字段
        studyid=custom_fields.get('studyid', ''),
        modalities=custom_fields.get('modalities', ''),
    )


def update_experiment(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, my_experiment: MyExperiment):
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}'
    experiment_params = my_experiment.model_dump(mode='json', exclude_unset=True, exclude={'label', 'studyid', 'modalities', 'acquisition_site'})
    experiment_params.update({
        f"{my_experiment.xsiType.value}/fields/field[name=studyid]/field": my_experiment.studyid,
        f"{my_experiment.xsiType.value}/fields/field[name=modalities]/field": my_experiment.modalities,
        f"{my_experiment.xsiType.value}/acquisition_site": my_experiment.acquisition_site,
    })

    response = session.put(url=url, params=experiment_params)
    return response.status_code, response.text
