import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from requests import Session
from tqdm import tqdm

from .CONFIG import URL


def upload_resources(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, scanID: str, parent_dir: str, *, resource_label: str = 'DICOM', content_description: str = '', max_workers: int = 3):
    failed = []  # 记录失败的文件
    parent_P = Path(parent_dir)
    file_list = list(parent_P.glob('**/*.dcm'))
    total_size = sum(f.stat().st_size for f in file_list)

    with tqdm(total=total_size, unit="B", unit_scale=True, unit_divisor=1024, desc="上传中") as bar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    __upload_resource,
                    session, projectID, subjectLabel, experimentLabel, scanID, fp, bar, resource_label, content_description
                )
                for fp in file_list
            ]
            for future in as_completed(futures):
                file_P, status_code, text = future.result()
                if status_code not in (200, 201):
                    failed.append((file_P, status_code, text))
        bar.set_description("✓ 上传完成")

    if failed:
        print(f"\n以下 {len(failed)} 个文件上传失败:")
        for file_P, code, msg in failed:
            print(f"  {file_P.name} -> HTTP {code}: {msg}")
    else:
        print(f"\n全部 {len(file_list)} 个文件上传成功!")

    return failed


# def upload_resources(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, scanID: str, parent_dir: str, *, resource_label: str = 'DICOM', content_description: str = '', max_workers: int = 3):
#     failed = []  # 记录失败的文件
#     parent_P = Path(parent_dir)
#     file_list = list(parent_P.glob('**/*.dcm'))
#
#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         futures = [
#             executor.submit(
#                 __upload_resource,
#                 session, projectID, subjectLabel, experimentLabel, scanID, fp, resource_label, content_description
#             )
#             for fp in file_list
#         ]
#
#         with tqdm(total=sum([file.stat().st_size for file in file_list]), unit="B", unit_scale=True, desc="上传中") as bar:
#             for future in as_completed(futures):
#                 file_P, status_code, text = future.result()
#                 if status_code not in (200, 201):
#                     failed.append((file_P, status_code, text))
#                 bar.update(file_P.stat().st_size)
#             bar.set_description("✓ 上传完成")
#
#     # 汇报失败情况
#     if failed:
#         print(f"\n以下 {len(failed)} 个文件上传失败:")
#         for file_P, code, msg in failed:
#             print(f"  {file_P.name} -> HTTP {code}: {msg}")
#     else:
#         print(f"\n全部 {len(file_list)} 个文件上传成功!")
#
#     return failed


def download_resources_by_scanIDs_or_scanTypes(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, scanIDs_or_scanTypes: list[str], save_dir: str):
    save_P = Path(save_dir) / 'downloads.zip'
    # 先获取文件大小
    url_1 = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}/scans/{','.join(scanIDs_or_scanTypes)}/resources'
    response_1 = session.get(url_1)
    result_1 = response_1.json()
    total = sum([int(item['file_size']) for item in result_1['ResultSet']['Result']])

    url_2 = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}/scans/{','.join(scanIDs_or_scanTypes)}/files?format=zip'
    response_2 = session.get(url=url_2, stream=True)
    with tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024, desc="下载中") as bar:
        with open(save_P, "wb") as f:
            for chunk in response_2.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
            bar.set_description("✓ 下载完成")
            bar.set_postfix(path=save_P.absolute())


def __upload_resource(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, scanID: str, file_path: str, bar: tqdm, resource_label: str = 'DICOM', content_description: str = '', max_retries: int = 5):
    file_P = Path(file_path)
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}/scans/{scanID}/resources/{resource_label}/files/{file_P.name}'
    upload_params = {
        'format': resource_label,
        'content': content_description,
        'inbody': 'true',
        'overwrite': 'true',
    }

    def read_with_progress(f):
        while chunk := f.read(8192):
            bar.update(len(chunk))
            yield chunk

    for attempt in range(max_retries):
        with open(file_P, "rb") as f:
            response = session.put(
                url,
                params=upload_params,
                data=read_with_progress(f),
            )

        if response.status_code in (200, 201):
            return file_P, response.status_code, response.text

        if response.status_code == 500 and 'catalog.xml' in response.text:
            # catalog.xml 冲突，重置进度条中本文件已更新的部分，随机等待后重试
            bar.update(-file_P.stat().st_size)
            time.sleep(3)
            continue
        # 其他错误直接返回，不重试
        break

    return file_P, response.status_code, response.text


def __upload_resource_deprecated(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, scanID: str, file_path: str, resource_label: str = 'DICOM', content_description: str = '', max_retries: int = 5):
    file_P = Path(file_path)
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}/scans/{scanID}/resources/{resource_label}/files/{file_P.name}'
    upload_params = {
        'format': resource_label,
        'content': content_description,
        'inbody': 'true',
        'overwrite': 'true',
    }

    # with open(file_P, "rb") as f:
    #     response = session.put(
    #         url,
    #         params=upload_params,
    #         data=f,
    #     )
    #
    # return file_P.name, response.status_code, response.text

    for attempt in range(max_retries):
        with open(file_P, "rb") as f:
            response = session.put(
                url,
                params=upload_params,
                data=f,
            )

        if response.status_code in (200, 201):
            return file_P.name, response.status_code, response.text

        if response.status_code == 500 and 'catalog.xml' in response.text:
            # catalog.xml 冲突，随机等待后重试
            # print('catalog.xml冲突了!')
            time.sleep(3)
            continue

        # 其他错误直接返回，不重试
        break

    return file_P, response.status_code, response.text


def __delete_resource(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, scanID: str, resource_label: str, file_name: str):
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}/scans/{scanID}/resources/{resource_label}/files/{file_name}'
    response = session.delete(url=url)
    return response.status_code, response.text


def __update_resource(session: Session, projectID: str, subjectLabel: str, experimentLabel: str, scanID: str, file_path: str, resource_label: str = 'DICOM', content_description: str = ''):
    file_P = Path(file_path)
    url = f'{URL}/data/projects/{projectID}/subjects/{subjectLabel}/experiments/{experimentLabel}/scans/{scanID}/resources/{resource_label}/files/{file_P.name}'
    upload_params = {
        'format': resource_label,
        'content': content_description,
        'inbody': 'true',
        'overwrite': 'true',
    }

    with open(file_P, "rb") as f:
        response = session.put(
            url,
            params=upload_params,
            data=f,
        )

    return response.status_code, response.text
