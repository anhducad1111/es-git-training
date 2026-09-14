# Product Requirement Document (PRD) — Central Telemetry & Data Management Backend
**Document Version:** 1.0  
**Target Audience:** Shodai Tokura (Backend & Data Engineer Intern)  
**Project:** Space Rover Central IoT Data Management Platform  
**Supervisor / Mentor:** Duke  

---

## 1. Executive Summary & Product Vision
The Space Rover is an autonomous and teleoperated exploration robot operating in remote or indoor environments. As the rover maneuvers, it continuously samples environmental parameters (temperature, humidity, air quality, obstacle distance) and diagnostic health states.

The **Central Telemetry Backend** acts as the brain and persistent memory of the entire rover fleet. It runs on the Central Gateway (Raspberry Pi 5) and is responsible for reliably collecting, validating, indexing, and serving rover data. It enables operators, analytics tools, and monitoring apps to understand the vehicle's historical performance and current environment.

---

## 2. Target Users & Core Personas
1. **Rover Pilot (Haru / Desktop Client):** Needs instant, low-latency access to the latest sensor readings and immediate warnings if an obstacle is within braking distance.
2. **Operations & Science Analyst:** Needs to query historical data over custom time windows (e.g., last 1 hour, today, past 7 days) to analyze environmental trends and detect anomalies (e.g., sudden temperature spikes or gas leaks).
3. **System Administrator:** Needs to check the health of the Central Gateway (CPU temperature, RAM, disk space, and data ingestion rates).

---

## 3. Comprehensive Feature Requirements

### 3.1. Telemetry Ingestion Pipeline (Data Intake)
* **Real-Time Data Ingestion:**
  - Must accept periodic high-frequency telemetry streams from the rover (typically sent every 1 to 5 seconds).
  - Must capture complete telemetry records: Device Identifier, Timestamp, Ambient Temperature (°C), Relative Humidity (%), Gas/Smoke Concentration Index (ppm), Ultrasonic Distance (cm), and Safety Auto-Brake Status.
* **Input Validation & Anomaly Sanitization:**
  - Automatically validate incoming sensor ranges (e.g., reject impossible temperature readings like 150°C or negative distance).
  - Reject corrupted or malformed payloads and log validation errors without crashing the service.
  - Return clear confirmation responses to sending nodes indicating successful storage.

### 3.2. Data Persistence & Timeseries Storage (Database)
* **Raw Timeseries Data Store:**
  - Store raw sensor logs with high timestamp precision.
  - Index data by device and timestamp to enable instantaneous queries even with hundreds of thousands of records.
* **Aggregated Historical Summaries:**
  - Compute and maintain periodic summaries (e.g., hourly and daily averages, minimums, and maximums) to enable fast long-term reporting without scanning entire raw log tables.

### 3.3. Client Query & Data Retrieval Services (API)
* **Instant Snapshot Query (Live Feed):**
  - Provide a dedicated ultra-fast query mechanism that returns solely the single latest reading from the rover, optimized for high-refresh client dashboards.
* **Range & Historical Queries:**
  - Allow clients to request the last $N$ records (e.g., latest 20, 50, 100 entries).
  - Support time-filtered queries (e.g., data between `start_time` and `end_time`) for plotting detailed graphs.
* **Summary & Analytics Reporting:**
  - Provide an endpoint delivering daily statistical highlights: Peak temperature, lowest temperature, average humidity, and total obstacle encounter count.
* **Data Export Capability:**
  - Support exporting queried historical data into standard structured formats (CSV / JSON) for external reporting.

### 3.4. Server Diagnostics & Health Monitoring
* **Gateway System Telemetry:**
  - Continuously report host performance metrics: CPU load percentage, CPU temperature, available RAM, and remaining storage on the Raspberry Pi 5.
  - Expose a simple health-check status indicating whether the database and web services are operating normally.

### 3.5. Automated Quality Assurance & Load Testing Suite
* **Rover Data Simulation Tool:**
  - Provide a standalone script that simulates one or multiple rovers sending continuous telemetry.
  - Measure backend performance under stress (e.g., handling 1,000 rapid requests without data loss or latency spikes).

---

## 4. User Stories & Acceptance Criteria

| User Story | Feature | Acceptance Criteria |
| :--- | :--- | :--- |
| *As a Rover Pilot, I want to request the newest rover data so that my dashboard displays real-time environmental status.* | Live Snapshot Query | Query returns the most recent record with all sensor fields in $< 30\text{ms}$. |
| *As an Analyst, I want to retrieve sensor history from the past hour so that I can plot trend graphs.* | Historical Data Query | Returns an array of chronologically sorted records within the specified time range or limit. |
| *As an Analyst, I want to see daily max/min temperatures so that I can evaluate extreme condition exposure.* | Statistical Summary | Endpoint outputs calculated min, max, and avg values for the requested time frame. |
| *As a System Admin, I want to monitor Raspberry Pi 5 health so that I know the server won't overheat or run out of disk.* | Gateway Health Check | Endpoint returns current CPU temp, RAM usage, and disk availability. |
| *As a Developer, I want invalid sensor data rejected so that our database remains clean and accurate.* | Data Validation | Payloads with out-of-range sensor readings or missing keys are cleanly rejected with appropriate error status. |

---

## 5. Design & Architectural Deliverables Expected from Intern
1. **Entity-Relationship Diagram (ERD) & Database Schema Design:** Documenting tables, field types, primary keys, and indexing strategy.
2. **RESTful API Proposal & Endpoint Contract:** Proposing URL routes, request methods, payload structures, and response formats.
3. **Data Flow & Sequence Diagram:** Illustrating how data flows from the Rover to the Database, and from the Database to client applications.
4. **Backend Implementation & Automated Test Suite:** Functional PHP/MariaDB codebase with a Python load-test tool.

---

## 6. Next Steps & Approval Workflow (Action Required First!)

> [!IMPORTANT]
> **Do NOT write backend implementation code yet!**  
> Follow this phased review process:
> 1. **Phase 1 (Your Design & Plan Proposal):** Read this PRD carefully, design your Database ERD, propose your API structure, and write your implementation plan.
> 2. **Phase 2 (Mentor Duke's Review & Approval):** Submit your design plan to mentor Duke for review and feedback.
> 3. **Phase 3 (Official API Documentation Unlocked):** Once your plan is officially approved by Duke, you will be handed the master API Documentation to begin implementation against the real hardware and server.


