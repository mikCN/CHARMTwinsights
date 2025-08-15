# Cox PH Model for COPD Prediction

This model implements a Cox Proportional Hazards model using lifelines for survival analysis of COPD. It predicts partial hazard scores and survival probabilities at 5 years based on a set of demographic and comorbidity features.

## Features

- **ethnicity**: Patient ethnicity
- **sex_at_birth**: Biological sex at birth  
- **obesity**: Binary indicator for obesity (0/1)
- **diabetes**: Binary indicator for diabetes (0/1)
- **cardiovascular_disease**: Binary indicator for cardiovascular disease (0/1)
- **smoking_status**: Smoking status (0.0 = Never, 1.0 = Current/Former)
- **alcohol_use**: Binary indicator for alcohol use (0/1)
- **bmi**: Body Mass Index
- **age_at_time_0**: Age at baseline

## Output

- **partial_hazard**: Relative risk compared to baseline
- **survival_probability_5_years**: Probability of survival at 5 years

## Model Details

Trained using Cox Proportional Hazards regression with lifelines library. Features are preprocessed using sklearn pipelines with imputation and standardization.

## Usage

The model accepts both single records and arrays of records. Each record should contain all the required features listed above.

## Example

```json
{
  "ethnicity": "Not Hispanic or Latino", 
  "sex_at_birth": "Female", 
  "obesity": 0.0, 
  "diabetes": 0.0, 
  "cardiovascular_disease": 0.0, 
  "smoking_status": 0.0, 
  "alcohol_use": 0.0, 
  "bmi": 25.0, 
  "age_at_time_0": 50.0
}
```

## Output Format

```json
{
  "partial_hazard": 0.866,
  "survival_probability_5_years": 0.963
}
```