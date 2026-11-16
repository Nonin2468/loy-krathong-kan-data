import json
import glob
import os
from datetime import datetime, timezone, timedelta

# ตั้งค่าเขตเวลาประเทศไทย (UTC+7)
THAI_TZ = timezone(timedelta(hours=7))
INTERVAL_SECONDS = 15  # ระยะห่างเวลาปล่อยระหว่างกระทงแต่ละใบ (วินาที)
BUFFER_SECONDS = 60    # เวลาเผื่อให้ GitHub อัปเดตไฟล์ (1 นาที)

MASTER_FILE = "krathongs_list.json"
SUBMISSIONS_DIR = "submissions/*.json"

def load_master():
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass
    return []

def main():
    master_list = load_master()
    existing_ids = {item.get("id") for item in master_list if "id" in item}
    
    # หาเวลาล่าสุดในคิวปัจจุบัน
    now_thai = datetime.now(THAI_TZ)
    last_scheduled_time = now_thai + timedelta(seconds=BUFFER_SECONDS)
    
    for item in master_list:
        if "spawn_time" in item and item["spawn_time"]:
            try:
                dt = datetime.fromisoformat(item["spawn_time"]).replace(tzinfo=THAI_TZ)
                if dt > last_scheduled_time:
                    last_scheduled_time = dt
            except ValueError:
                pass

    # วนอ่านไฟล์ทั้งหมดใน submissions/ เรียงตามชื่อไฟล์
    submission_files = sorted(glob.glob(SUBMISSIONS_DIR))
    added_count = 0

    for file_path in submission_files:
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"❌ ข้ามไฟล์ (JSON พัง): {file_path}")
                continue

        if not isinstance(data, dict):
            continue

        # ใช้ชื่อไฟล์เป็น id ถ้าไม่ได้ระบุมา (ป้องกันการเพิ่มซ้ำ)
        item_id = data.get("id") or os.path.splitext(os.path.basename(file_path))[0]
        if item_id in existing_ids:
            continue

        data["id"] = item_id
        
        # 🕒 คำนวณเวลาปล่อยตามคิว (ต่อจากใบล่าสุด + INTERVAL_SECONDS)
        next_spawn_time = last_scheduled_time + timedelta(seconds=INTERVAL_SECONDS)
        data["spawn_time"] = next_spawn_time.strftime("%Y-%m-%dT%H:%M:%S")
        last_scheduled_time = next_spawn_time

        # จัดลำดับ slot_index ให้อัตโนมัติถ้าไม่ได้ใส่มา
        if "slot_index" not in data:
            data["slot_index"] = len(master_list) + 1

        master_list.append(data)
        existing_ids.add(item_id)
        added_count += 1
        print(f"✅ จัดคิวสำเร็จ: {data.get('author', item_id)} -> ปล่อยเวลา {data['spawn_time']}")

    if added_count > 0:
        with open(MASTER_FILE, "w", encoding="utf-8") as f:
            json.dump(master_list, f, ensure_ascii=False, indent=2)
        print(f"🎉 อัปเดต {MASTER_FILE} เรียบร้อย (เพิ่มใหม่ {added_count} รายการ)")
    else:
        print("ℹ️ ไม่มีกระทงใหม่ที่ต้องจัดคิว")

if __name__ == "__main__":
    main()
