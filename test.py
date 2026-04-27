import requests, urllib3

urllib3.disable_warnings()

s = requests.Session()
s.auth = ("admin", "uy*96+UU;")
s.verify = False

BASE = "https://xnat.pemed.cn:9443"
PROJECT = "SYOncologySR"
SESSION = "SYZLXNAT_E00127"
SCAN_ID = "CT_Series7_183"
ARCHIVE_URI = "/data/xnat/archive/SYOncologySR/arc001/study_1_2025-05-15-015/SCANS/CT_Series7_183/DICOM"

# ── Step 1：触发 catalog refresh，重建 SOP UID 索引 ──
print("Step 1: 触发 catalog refresh...")
resp = s.post(
    f"{BASE}/data/services/refresh/catalog",
    params={
        "resource": ARCHIVE_URI,
        "fixmissing": "true",  # 补全缺失的 SOP UID 索引
        "fixduplicates": "true"
    }
)
print(f"  结果：{resp.status_code}  {resp.text[:200]}")

# ── Step 2：再次刷新 ROI 插件缓存 ──────────────────
print("\nStep 2: 刷新 ROI sdcache...")
resp = s.post(
    f"{BASE}/xapi/roi/projects/{PROJECT}/sdcache/{SESSION}",
    params={"cmd": "REFRESH"}
)
print(f"  结果：{resp.status_code}  {resp.text}")

# ── Step 3：验证 SOP UID 数量 ──────────────────────
print("\nStep 3: 验证 SOP UID...")
resp = s.get(
    f"{BASE}/xapi/roi/projects/{PROJECT}"
    f"/sessions/{SESSION}/scans/{SCAN_ID}/uids"
)
uids = resp.json()
print(f"  SOP UID 数量：{len(uids)}")

# ── Step 4：数量正确则上传 RS.dcm ──────────────────
if len(uids) == 183:
    print("\nStep 4: 上传 RS.dcm...")
    from pathlib import Path

    RS_PATH = Path("/Users/kukudehui/Desktop/XNAT_DATA/sorted_data/"
                   "2025-05-15-015/study_1_1.2.40.0.13.1.1.192.192.186.171.20250520070000051.32841/"
                   "RS_RTSTRUCT/Series7_1/RS.2025-05-15-015.SS1.dcm")
    resp = s.put(
        f"{BASE}/xapi/roi/projects/{PROJECT}"
        f"/sessions/{SESSION}/collections/RS_PatientA",
        params={"type": "RTSTRUCT", "overwrite": "false"},
        headers={"Content-Type": "application/octet-stream"},
        data=RS_PATH.read_bytes()
    )
    print(f"  上传结果：{resp.status_code}  {resp.text}")
    if resp.status_code in (200, 201):
        print("\n✓ 成功！打开 OHIF Viewer 查看轮廓。")
else:
    print(f"\n⚠ SOP UID 仍为 {len(uids)} 个，尝试备用方案...")
    # 备用：通过 experiment 级别触发全量 refresh
    resp = s.post(
        f"{BASE}/data/services/refresh/catalog",
        params={
            "resource": f"/data/xnat/archive/SYOncologySR/arc001/study_1_2025-05-15-015",
            "fixmissing": "true",
            "fixduplicates": "true"
        }
    )
    print(f"  全量 refresh：{resp.status_code}  {resp.text[:200]}")
