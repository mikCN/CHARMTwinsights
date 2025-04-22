
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

- Synthetic data generation
- Cohort management
- Longitudinal patient views
- Model execution and result serving

---

## 2. System Architecture Context

The API is deployed as part of a modular Dockerized system, and interfaces with:

- **HAPI-FHIR Server** for EHR data ingestion and queries
- **PostgreSQL Database** as backend storage
- **Python and R Analytics Containers**
- **Planned Imputation and OMOP Mapping Services**
- **External UI or CLI clients**

---

## 3. Endpoint Groups and Examples

### 3.1 Synthetic Data Generation

**Endpoint:** `POST /api/synthetic/generate-patients`

**Python Example:**

```python
import requests
url = f"{BASE_URL}/api/synthetic/generate-patients"
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
  {"cohortId": "cohort-1234", "name": "Diabetes Patients Over 50", "size": 42}
]
```

---

### 3.3 Statistics

**Endpoints:**

- `GET /api/statistics/cohort/{id}/summary`
- `GET /api/statistics/cohort/{id}/demographics`
- `GET /api/statistics/cohort/{id}/conditions`
- `GET /api/statistics/cohort/{id}/medications`
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

**Endpoints:**

- `POST /api/models/upload`
- `GET /api/models/{id}`
- `DELETE /api/models/{id}`
- `POST /api/models/{id}/predict/patient/{pid}`
- `POST /api/models/{id}/predict/cohort/{cid}`

**Python Example (Single Patient Prediction):**

```python
url = f"{BASE_URL}/api/models/model-abc123/predict/patient/patient-001"
payload = {"patientId": "patient-001"}
response = requests.post(url, json=payload)
print(response.json())
```

**Response Example:**

```json
{
  "patientId": "patient-001",
  "modelId": "model-abc123",
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

- Michele Esposito – Lead PM / Integration
- Shawn O. – Infrastructure & Docker
- Anas – API architecture & cohort logic
- Additional collaborators: TISLab, CU, CHARM-GPT team
