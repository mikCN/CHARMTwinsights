# CHARMTwinsight – Predictive Analytics API Design Document

**Deliverable:** C3.Y1.D1.5-D  
**Due Date:** May 26, 2025  
**Lead Institution:** Maastricht University  
**Repository:** [https://github.com/mikCN/CHARMTwinsights/](https://github.com/mikCN/CHARMTwinsights/)

---

## 1. Overview

CHARMTwinsight is a multimodal digital twin repository for structured and unstructured healthcare data.  
This API is designed to serve as the primary interface to query, analyze, and manage synthetic and real patient data within the repository.

It will support:

- Synthetic patients data generation (by condition, by an age range, etc.)
- Cohort management
- Longitudinal patient views
- Model execution and result serving

---

## 2. System Architecture Context

The API is deployed as part of a modular Dockerized system, and interfaces with:

- **HAPI-FHIR Server** to serve as repository for EHR data ingestion and queries
- **PostgreSQL Database** as backend storage
- **Python and R Analytics Containers**
- **Repository for predictive models (e.g. ML Flow models)**
- **MinIO Database** or other S3-compatible object storage for models
- **Planned Imputation and OMOP Mapping Services**
- **External UI or CLI clients**

---

## 3. Endpoint Groups and Examples

### 3.1 Synthetic Data Generation

Synthetic data generation can be accomplished by multiple methods, including
the Synthea cohort builder and GAN-based generative models. Generated
data are stored in the HAPI-fhir server for further use and reference.

**Endpoints:** 
`POST /api/synthetic/generate-patients`
`GET /api/synthetic/synthea-modules` # get list of modules available to synthea
`GET /api/synthetic/synthea-module/{module_name}` # get specific module information


**Python Example:**

```python
import requests
url = f"{BASE_URL}/api/synthetic/generate-patients"
method = {"SYNTHEA"} # "SYNTHEA" or "GAN"
payload = {
  "count": 100,
  "demographics": {
    "age_range": [40, 65],
    "gender_distribution": {"M": 0.4, "F": 0.6}
  },
  "disease_prevalence": {
    "hypertension": 0.3,
    "diabetes": 0.1
  }
}
response = requests.post(url, json=payload)
print(response.json())
```

**Response Example:**

```json
{
  "patients": [
    {
      "id": "patient-001",
      "gender": "Female",
      "birthDate": "1950-06-24",
      "conditions": [
        {"code": "E11", "description": "Type 2 diabetes mellitus"}
      ]
    }
  ]
}
```

---

### 3.2 Cohort Management

Generated synthetic cohorts may be listed, removed, and merged, 
allowing high-level data organization.

**Endpoints:**

- `GET /api/data-management/cohorts`
- `GET /api/data-management/cohorts/{id}`
- `DELETE /api/data-management/cohorts/{id}`
- `POST /api/data-management/cohorts/merge`

**Python Example (List Cohorts):**

```python
url = f"{BASE_URL}/api/data-management/cohorts"
response = requests.get(url)
print(response.json())
```

**Response Example:**

```json
[
  {"cohortId": "cohort-1234", "name": "Diabetes Patients Over 50", "size": 42},
  {"cohortId": "cohort-54", "name": "General population, 20 to 65", "size": 2000},
]
```

---

### 3.3 Statistics

Basic summary statistics support cursory views of synthetic cohorts. 

**Endpoints:**

- `GET /api/statistics/cohort/{id}/summary`
- `GET /api/statistics/cohort/{id}/demographics`
- `GET /api/statistics/cohort/{id}/conditions`
- `GET /api/statistics/cohort/{id}/medications`
- `GET /api/statistics/cohort/{id}/comorbidities`
- `POST /api/statistics/cohort/{id}/custom-metric`

**Python Example (Summary):**

```python
url = f"{BASE_URL}/api/statistics/cohort/cohort-1234/summary"
response = requests.get(url)
print(response.json())
```

**Response Example:**

```json
{
  "cohortId": "cohort-1234",
  "averageAge": 64.5,
  "genderDistribution": {"male": 22, "female": 20}
}
```

---

### 3.4 Longitudinal Patient Views

Longitudinal patient views of synthetic patients and cohorts provide 
detailed views, of use for model training or other CHARM components.

**Endpoints:**

- `GET /api/longitudinal/patients/{id}/timeline`
- `GET /api/longitudinal/patients/{id}/observation-series`
- `GET /api/longitudinal/patients/{id}/medication-timeline`
- `GET /api/longitudinal/patients/{id}/condition-progression`

**Python Example (Timeline):**

```python
url = f"{BASE_URL}/api/longitudinal/patients/patient-001/timeline"
response = requests.get(url)
print(response.json())
```

**Response Example:**

```json
[
  {"date": "2015-01-10", "type": "Condition", "description": "Diagnosed with Type 2 diabetes"},
  {"date": "2015-01-15", "type": "Medication", "description": "Started Metformin"}
]
```

---

### 3.5 Model Storage and Execution

CHARMTwinsight will serve predictive models via REST, allowing uploads of 
packaged ML and statistical models. An abstracted API
with consistent metadata requirements will allow models to define their own 
feature inputs and outputs, which may include POSTed data or CHARMTwinsight 
cohorts or patients via reference identifier. These models may be developed
or used by the broader CHARM ecosystem.

**Endpoints:**

- `POST /api/models/upload`
- `GET /api/models/all`
- `GET /api/models/{id}` # get metadata for model usage
- `DELETE /api/models/{id}`
- `POST /api/models/predict`

**Python Example (Single Patient Prediction):**

```python
url = f"{BASE_URL}/api/models/sepsis_model/predict"
payload = {"data": [{"pt_age": 26, "pt_bmi": 31, "pt_copd": True, "pt_heartrate": 86}]}
response = requests.post(url, json=payload)
print(response.json())
```

**Response Example:**

```json
{
  "modelId": "sepsis_model",
  "predictions": {"riskScore": 0.82, "riskLevel": "High"}
}
```

---

## 4. Data Format & Standards

- Data input/output will conform to HL7 FHIR R4 for clinical content
- JSON will be the standard payload format
- LLM embeddings used for GAN conditioning will be provided as vectors
- Tabular output will support CSV or DataFrame-style objects for statistical pipelines

---

## 5. Security & Access (Planned)

- REST API will be accessible via secure HTTPS
- Authentication via API key or OAuth2 token (TBD)
- Permissions may be role-based in federated environments

---

## 6. Roadmap

| Milestone | Description                       | Target      |
| --------- | --------------------------------- | ----------- |
| v0.1      | Internal endpoint scaffolding     | April 2025  |
| v0.2      | Integrated with Python container  | May 2025    |
| v1.0      | Public endpoints & UI integration | August 2025 |

---

## 7. Contributors
- Michele Esposito - Maastricht University
- Michel Dumontier - Maastricht University
- Anas Elghafari - Maastricht University
- Shawn O'Neil - TISLab
