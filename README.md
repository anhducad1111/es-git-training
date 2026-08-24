# Mini-Project: Sensor Logger & Git Teamwork

**Goal:** A realistic 2-day corporate onboarding project to practice professional Git workflow (branching, commits, Pull Requests, Peer & Mentor Code Reviews) and verify basic client-server communication.

**Roles:**
* **Mentor (Lead Engineer):** Duke (Reviews PRs, provides technical feedback, approves merge into `dev`).
* **Haru (Intern):** Python Client Engineer.
* **Shodai (Intern):** Backend & Database Engineer (Local Windows XAMPP).

---

## 1. What to Build

```text
+---------------------------------+             +---------------------------------+
|      Haru (Python Client)       |             |      Shodai (Local Server)      |
|                                 |  HTTP POST  |    (Windows: XAMPP / Apache)    |
| - Simple GUI (Tkinter or PyQt)  | ----------> | - `POST /api/log.php` (Save DB) |
| - Enter sensor values (Temp/Hum)|             | - `GET /api/log.php`  (Get DB)  |
| - "Send" button & history view  |  HTTP GET   | - MySQL Database (`mini_db`)    |
|                                 | <---------- |                                 |
+---------------------------------+             +---------------------------------+
```

### **Shodai — Local Backend (Windows XAMPP):**
1. **Database (`mini_db` in MySQL):**
   * Table `sensor_logs`: `id`, `device_name`, `temperature`, `humidity`, `created_at`.
2. **REST API (`api/log.php`):**
   * `POST /api/log.php`: Receive JSON `{"device": "Haru-Client", "temp": 28.5, "humidity": 65}` and save to MySQL.
   * `GET /api/log.php`: Return the latest 10 records as JSON.

### **Haru — Python Client (`mini_client/app.py`):**
1. **Simple GUI window:**
   * Input box for Shodai's IP (e.g. `http://192.168.1.100/api/log.php`).
   * Sliders or input fields for **Temperature** and **Humidity**.
   * **"Send Data"** button $\rightarrow$ sends HTTP POST to Shodai's server.
   * **"Refresh List"** button $\rightarrow$ fetches and shows recent records from Shodai's server.

---

## 2. Professional Git Workflow (Company Standard)

```text
[main] ─────────────────────────────────────────────────────────── (Stable Production)
   │
[dev]  ─────────────────────────────────────────────────────────── (Active Development)
   │
   ├── [feat/shodai-api] ──> PR to dev ──> (Haru & Mentor Duke Review) ──> Merge into dev
   │
   └── [feat/haru-client] ─> PR to dev ──> (Shodai & Mentor Duke Review) ─> Merge into dev
```

1. **Clone Repo & Switch to `dev`:**
   ```bash
   git clone <repo_url>
   git checkout dev
   ```
2. **Create Feature Branch from `dev`:**
   * Shodai: `git checkout -b feat/shodai-api`
   * Haru: `git checkout -b feat/haru-client`
3. **Commit & Push:** Follow clear commit conventions (e.g., `feat: create sensor log api`).
4. **Pull Request (PR) into `dev` & Dual Review:**
   * Target base branch for PR must be **`dev`** (NOT `main`).
   * **Step 4a (Peer Review):** Shodai and Haru review each other's code, test the interface, and leave comments.
   * **Step 4b (Mentor Review):** Mentor **Duke** conducts formal code review, requests changes (if any), and gives final **Approval**.
5. **Merge & Live Test:** Merge approved PRs into **`dev`**, pull the latest `dev` code, and test the full flow together over Wi-Fi:
   ```bash
   git checkout dev
   git pull origin dev
   ```

---

## 3. Schedule

* **Day 1 (Mon):** Setup dev environment (XAMPP for Shodai, Python for Haru) $\rightarrow$ Create feature branches from `dev` $\rightarrow$ Implement code.
* **Day 2 (Tue):** Open Pull Requests to `dev` $\rightarrow$ Peer review $\rightarrow$ **Mentor Duke reviews and approves** $\rightarrow$ Merge into `dev` $\rightarrow$ Live demo over Wi-Fi.
