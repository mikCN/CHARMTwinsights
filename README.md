# CHARMTwinsight

## 📌 Overview
This repository provides a **data ingestion pipeline** that loads **synthetic patient data** (generated using [Synthea](https://github.com/synthetichealth/synthea)) into a **HAPI-FHIR server**. The goal is to test and validate **CHARMTwinsight's** ability to process US Core-compliant **FHIR** patient records.

## 🏥 What is FHIR and HAPI-FHIR?
- **FHIR (Fast Healthcare Interoperability Resources)** is a **standard** for exchanging healthcare data electronically.
- **HAPI-FHIR** is an **open-source implementation** of FHIR, providing a Java-based **FHIR server** for storing and querying patient records.
- CHARMTwinsight **ingests patient data from HAPI-FHIR**, enabling further analysis for digital twins in healthcare.

## 🏗 Repository Structure
```
📦 CHARMTwinsight-Synthea-Ingestion
 ┣ 📂 data/                     # Stores generated synthetic patient data
 ┃ ┣ 📂 fhir/                   # FHIR-formatted patient records
 ┃ ┣ 📂 metadata/               # Metadata from Synthea
 ┣ 📂 scripts/                  # Python scripts for data processing
 ┃ ┣ 📜 fhir_upload_script.py       # Main script to upload data to HAPI-FHIR
 ┣ 📜 README.md                 # Project documentation (this file)
```

## ⚙️ Installation & Setup

### 1️⃣ Install Dependencies
Ensure **Python 3.8+** is installed, then install required dependencies:
```sh
pip install -r requirements.txt
```

### 2️⃣ Generate Synthetic Data with Synthea
To create **20 synthetic patients** with **US Core-compliant FHIR format**:
```sh
java -jar synthea-with-dependencies.jar -p 20 -a 1-90 -s 123 --exporter.fhir.use_us_core_ig true
```
- `-p 20` → Generates **20 patients**.
- `-a 1-90` → Random **ages between 1-90**.
- `-s 123` → Uses **seed 123** for reproducibility.
- `--exporter.fhir.use_us_core_ig true` → Ensures **US Core compliance**.

Download the .jar file from [here](https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar) 
Check output example in .zip format. (.\data)

### 3️⃣ Start HAPI-FHIR Server (Docker)
If running **HAPI-FHIR locally**, use Docker:
```sh
docker run -d -p 8080:8080 hapiproject/hapi:latest
```
Once running, access the **FHIR UI** at:
[http://localhost:8080/](http://localhost:8080/)

### 4️⃣ Upload Synthetic Data
Run the Python script to **upload patient data** to HAPI-FHIR:
```sh
python scripts/fhir_upload_script.py
```

## 🚀 How `fhir_upload_script.py` Works

This script **uploads FHIR JSON files** to the **HAPI-FHIR server**:

### 🔹 **Workflow**
1. Scans the `data/fhir/` directory for **FHIR JSON files**.
2. Identifies whether the file contains **a single resource** or **a full FHIR Bundle**.
3. Sends data to the **appropriate HAPI-FHIR endpoint**:
   - **Bundles** → Sent to `/fhir/`
   - **Single resources** → Sent to `/fhir/{resourceType}` (e.g., `/fhir/Patient`)
4. Logs **successful or failed uploads**.

###📌 **Next Steps & Extensions**

🔹 Upcoming Features:
✅ Automate bulk uploads (batch processing).
✅ Support real patient ingestion from external FHIR-HOSE pipelines.
✅ Enhance storage layer for analytics & machine learning.

## 📜 License
This repository is licensed under **MIT License**. See [`LICENSE`](LICENSE) for details.

## 📩 Contact
For questions, reach out via **GitHub Issues** or email **m.esposito@maastrichtuniversity.nl**.
