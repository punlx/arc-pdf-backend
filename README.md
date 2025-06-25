## ➤ Run locally with Docker‑Compose

```bash
# 1. clone + cd
$ git clone https://github.com/punlx/arc-pdf-backend.git

# 2. start everything
$ docker compose up --build
```

# ArcPDF Backend – เปรียบเทียบ **v1** และ **v2**

> เอกสารนี้อธิบาย **ความแตกต่างหลัก** ระหว่างเวอร์ชัน `v1` และ `v2` ของบริการ FastAPI สำหรับโปรเจกต์ ArcPDF พร้อมสรุปเหตุผลในการปรับปรุงและผลกระทบที่ตามมา เพื่อให้ผู้พัฒนา / ผู้รีวิวโค้ดเข้าใจและวางแผน migration ได้ง่ายขึ้น

---

## 🗂️ สรุปความเปลี่ยนแปลงแบบย่อ

| หมวด                | v1                                           | v2                                                               | ประโยชน์ที่ได้                                               |
| ------------------- | -------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------ |
| **CORS**            | อนุญาตทุก origin (`*`)                       | ล็อก origin ให้เฉพาะ `localhost:5173` และ `arc-pdf.onrender.com` | เพิ่มความปลอดภัย ป้องกัน CSRF & สคริปต์ข้ามโดเมน             |
| **Session Model**   | `uploaded_files: List` แชร์ไฟล์ทุกแชตร่วมกัน | `uploaded_files: Dict[chat_id, List]` แยกไฟล์ตาม session         | ไม่มีการปนกันของไฟล์ – แต่ละแชตเห็นเฉพาะไฟล์ของตัวเอง        |
| **Memory Tracking** | ไม่มีเวลาใช้งานล่าสุด                        |  เพิ่ม `chat_last_active` และ `touch_chat()`                     | เรียงรายการแชตตามกิจกรรมล่าสุดได้ถูกต้อง                     |
| **ขนาดไฟล์**        | ไม่จำกัด                                     | จำกัดที่ 10 MB ( `MAX_FILE_SIZE` )                               | ลดความเสี่ยง DoS ด้วยไฟล์ใหญ่เกิน                            |
| **/api/upload**     | `POST` รอ *body* `files[]` เท่านั้น          | รับ `chat_id` ผ่าน query param (สร้างใหม่อัตโนมัติถ้าไม่มี)      | แนบไฟล์ถูกผูกกับ session ตั้งแต่ต้น – frontend ระบุได้ชัดเจน |
| **/api/files**      | คืนไฟล์ทั้งหมดทุกแชต                         | ต้องส่ง `chat_id` เพื่อดึงไฟล์ของแชตนั้น ๆ                       | ความเป็นส่วนตัวของแต่ละ session                              |
| **Endpoints เพิ่ม** | –                                            | `DELETE /api/files/{file_id}` และ `DELETE /api/files`            | ลบไฟล์รายตัว / ลบยกชุดใน session                             |
| **WebSocket**       | ไม่แยก session ถ้าไม่ส่ง `chat_id`           | สร้าง `chat_id` ใหม่ให้เสมอ & ใช้ไฟล์เฉพาะ session               | ทำงานร่วมกับ frontend ที่ multi‑chat ได้สมบูรณ์ขึ้น          |
| **Reset Logic**     | `reset()` ลบเฉพาะ chat_history               | เพิ่ม flag `clear_files` เลือกรีเซตไฟล์ด้วย                      | Full‑reset เคลียร์ได้ทั้งประวัติและไฟล์                      |
| **Sorting Chats**   | ไม่กำหนด                                     | เรียงตาม `last_active_time` (DESC)                               | UX ดีกว่า – แชตที่เพิ่งคุยขึ้นก่อน                           |
| **HTTP Status**     | 400 ทั่วไป                                   | ใช้ `413` สำหรับไฟล์ใหญ่เกิน                                     | สื่อความหมาย RFC ชัดเจน                                      |

---

## 🔍 รายละเอียดการปรับปรุงใน `v2`

### 1 · Session‑aware Storage

- `MemoryStore.uploaded_files` เปลี่ยนเป็น `Dict[str, List[fileMeta]]` แยกไฟล์ต่อ `chat_id`
- เมท็อดใหม่:
  - `add_files(chat_id, files)` – บันทึกไฟล์ลง session
  - `get_files(chat_id)` – ดึงไฟล์เฉพาะ session
  - `delete_file()` & `clear_files()` – จัดการไฟล์รายตัว/ทั้งหมด

### 2 · กำหนดขอบเขต CORS ชัดเจน

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://arc-pdf.onrender.com",
    ],
    ...
)
```

ลดพื้นผิวโจมตี โดยอนุญาตเฉพาะโดเมนที่ใช้จริงระหว่าง dev และ prod

### 3 · Upload Endpoint ที่รับรู้ chat_id

- signature ใหม่: `POST /api/upload?chat_id=...`
- ถ้า `chat_id` ยังไม่ถูกสร้าง จะสร้าง session ให้ก่อนอัตโนมัติ
- ไฟล์ทั้งหมดถูกเก็บแยกตาม session ตั้งแต่แรก รับประกัน isolation

### 4 · ขีดจำกัดขนาดไฟล์ & ประเภทไฟล์

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
if len(content) > MAX_FILE_SIZE:
    raise HTTPException(413, "... exceeds 10 MB")
```

ป้องกันผู้ใช้ อัปโหลดไฟล์ใหญ่เกินโดยไม่ตั้งใจ และป้องกัน DoS

### 5 · WebSocket Flow ใหม่ (Session‑aware)

- ถ้า payload ไม่ระบุ `chat_id` → backend สร้าง session ใหม่ให้
- ใช้ `memory.get_files(chat_id)` เพื่อให้คำตอบอิงจากไฟล์เฉพาะแชต
- ยังคงส่ง `typing → chunk → complete` แต่ระบุ `chat_id` กลับไปชัดเจน

### 6 · การจัดอันดับแชตตามการใช้งานล่าสุด

- เพิ่ม `chat_last_active: Dict[chat_id, ISOTime]` - เรียก `touch_chat(chat_id)` ทุกครั้งที่ front‑end เปิดหน้าต่างแชตแม้ไม่ส่งข้อความ - `GET /api/chat` จะ `sort` ตาม `last_active_time DESC` เพื่อ UX ที่คุ้นเคย (คล้าย Slack / Messenger)

### 7 · Endpoint ลบไฟล์

```
DELETE /api/files/{file_id}?chat_id=...
DELETE /api/files?chat_id=...        # ลบหมดในแชตนั้น
```

เปิดทางให้ UI จัดการไฟล์ทีละไฟล์หรือยกชุดในแต่ละ session ได้

### 8 · Reset Endpoint ที่ยืดหยุ่นขึ้น

- พารามิเตอร์ `clear_files` ช่วยเลือกได้ว่าจะลบไฟล์ด้วยหรือไม่
- Full Reset (`chat_id=None`) → ล้างทั้ง chat และ files, ออก `session_id` ใหม่

---

## 🔄 คู่มือ Migration Frontend

1. **อัปโหลดไฟล์**
   - ต้องใส่ `chat_id` เป็น query string เช่น `POST /api/upload?chat_id=<uuid>`
   - สร้างแชตใหม่ได้ผ่าน `/api/chat/create` ก่อนอัปโหลด
2. **ดึงรายชื่อไฟล์**
   - เรียก `GET /api/files?chat_id=<uuid>`
3. **ลบไฟล์**
   - เพิ่มปุ่มใน UI → `DELETE /api/files/{file_id}?chat_id=<uuid>`
4. **WebSocket**
   - ใส่ `chat_id` ใน payload ทุกครั้ง
   ```json
   { "question": "...", "chat_id": "..." }
   ```
5. **เรียงลำดับแชต**
   - ใช้ฟิลด์ `last_active_time` จาก `GET /api/chat` แทน `last_message_time`

---
