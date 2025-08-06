# Cox PH Model for COPD Prediction

**Author:** Lakshmi Anandan  
**Description:** A survival model to predict risk and survival probability for COPD based on demographics and comorbidities.  
**Framework:** `lifelines`, `scikit-learn`  

## Details

This model implements a Cox Proportional Hazards (CoxPH) model using `lifelines` for survival analysis of Chronic Obstructive Pulmonary Disease (COPD). It was trained on the All of Us Research Program data and is designed to predict an individual's relative risk score and their probability of remaining free from a COPD event over a specific time horizon. The model's inputs are based on a set of demographic, comorbidity, and behavioral features defined by concepts.

## Input Features Expected

The model expects a JSON-formatted array of inputs, where each object in the array represents a single patient record. The keys and their potential values are as follows:

* `ethnicity` (Categorical): One of `Not Hispanic or Latino`, `PMI: Prefer Not To Answer`, `PMI: Skip`, `What Race Ethnicity: Race Ethnicity None Of These`
* `sex_at_birth` (Categorical): One of `Male`, `Female`, `I prefer not to answer`, `No matching concept`, `None`, `PMI: Skip`
* `obesity` (Binary)
* `diabetes` (Binary)
* `cardiovascular_disease` (Binary)
* `smoking_status` (Binary)
* `alcohol_use` (Binary)
* `bmi` (Continuous)
* `age_at_time_0` (Continuous)

## Example Input

```json
[
  {
    "ethnicity": "Not Hispanic or Latino",
    "sex_at_birth": "Male",
    "obesity": 1.0,
    "diabetes": 0.0,
    "cardiovascular_disease": 1.0,
    "smoking_status": 0.0,
    "alcohol_use": 0.0,
    "bmi": 28.5,
    "age_at_time_0": 65.0
  },
  {
    "ethnicity": "Hispanic or Latino",
    "sex_at_birth": "Female",
    "obesity": 0.0,
    "diabetes": 1.0,
    "cardiovascular_disease": 0.0,
    "smoking_status": 0.0,
    "alcohol_use": 1.0,
    "bmi": 32.1,
    "age_at_time_0": 72.0
  }
]