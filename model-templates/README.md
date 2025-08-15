# CHARMTwinsights Model Development Guide

This guide helps you create and deploy machine learning models for CHARMTwinsights without needing to be a Docker expert.

## Quick Start

1. **Choose your language**: Copy the appropriate template
   - Python: `cp -r python-model my-model`
   - R: `cp -r r-model my-model`

2. **Develop your model**: Replace the template code with your model

3. **Validate**: Run `python validate-dockerfile.py my-model/Dockerfile`

4. **Build**: `docker build -t my-model:latest my-model/`

5. **Register**: Use the API to register your model

## Template Overview

### Files You Need

```
my-model/
├── Dockerfile          # Container definition (minimal editing needed)
├── predict.py/.R        # Your prediction code (EDIT THIS)
├── predict              # Execution script (don't modify)
├── README.md            # Model documentation (EDIT THIS)
├── examples.json        # Test examples (EDIT THIS)
├── pyproject.toml       # Python deps (EDIT THIS)
└── DESCRIPTION          # R deps (EDIT THIS)
```

### Critical Rules

**NEVER add these to your Dockerfile:**
- `CMD` or `ENTRYPOINT` directives
- These break integration with the model server

**Always include:**
- A working `/predict` script
- `README.md` with model documentation
- `examples.json` with valid test data

## Python Models

### 1. Copy Template
```bash
cp -r model-templates/python-model my-python-model
cd my-python-model
```

### 2. Edit Dependencies
Update `pyproject.toml` with your required packages:
```toml
[tool.poetry.dependencies]
python = "^3.11"
scikit-learn = "^1.3.0"
torch = "^2.0.0"  # Add your packages here
```

### 3. Implement Your Model
Edit `predict.py`:

```python
def load_model():
    # Load your trained model
    return joblib.load('my_model.pkl')

def preprocess_input(input_data):
    # Your preprocessing logic
    return processed_data

def postprocess_output(predictions, input_data):
    # Format your outputs
    return results
```

### 4. Update Metadata
- Edit `README.md` with your model description
- Edit `examples.json` with valid test inputs
- Copy your model files (`.pkl`, `.joblib`, etc.) and update Dockerfile

### 5. Test and Deploy
```bash
# Validate Dockerfile
python ../validate-dockerfile.py Dockerfile

# Build image
docker build -t my-python-model:latest .

# Register with CHARMTwinsights
curl -X POST http://localhost:8000/modeling/models \
  -H "Content-Type: application/json" \
  -d '{
    "image": "my-python-model:latest",
    "title": "My Python Model",
    "short_description": "Description of what it does",
    "authors": "Your Name"
  }'
```

## R Models

### 1. Copy Template
```bash
cp -r model-templates/r-model my-r-model
cd my-r-model
```

### 2. Edit Dependencies
Update `DESCRIPTION` with your required R packages:
```
Imports: 
    jsonlite,
    readr,
    randomForest,
    caret
```

### 3. Implement Your Model
Edit `predict.R`:

```r
load_model <- function() {
  # Load your trained model
  return(readRDS("my_model.rds"))
}

preprocess_input <- function(input_data) {
  # Your preprocessing logic
  return(processed_data)
}

postprocess_output <- function(predictions, input_data) {
  # Format your outputs
  return(results)
}
```

### 4. Update Metadata
- Edit `README.md` with your model description
- Edit `examples.json` with valid test inputs  
- Copy your model files (`.rds`, `.RData`, etc.) and update Dockerfile

### 5. Test and Deploy
```bash
# Validate Dockerfile
python ../validate-dockerfile.py Dockerfile

# Build image
docker build -t my-r-model:latest .

# Register with CHARMTwinsights
curl -X POST http://localhost:8000/modeling/models \
  -H "Content-Type: application/json" \
  -d '{
    "image": "my-r-model:latest",
    "title": "My R Model", 
    "short_description": "Description of what it does",
    "authors": "Your Name"
  }'
```

## API Registration

### Container-Based Metadata (Recommended)
If your model includes `README.md` and `examples.json`, you only need:

```json
{
  "image": "my-model:latest",
  "title": "Model Title",
  "short_description": "Brief description", 
  "authors": "Your Name"
}
```

The README and examples will be extracted from the container automatically.

### Full API Metadata
You can also provide everything via API:

```json
{
  "image": "my-model:latest",
  "title": "Model Title",
  "short_description": "Brief description",
  "authors": "Your Name",
  "examples": [{"feature1": 1.0, "feature2": "value"}],
  "readme": "# My Model\nDescription..."
}
```

API-provided metadata always overrides container metadata.

## Input/Output Format

### Input Format
Your model receives JSON data:
```json
[
  {"feature1": 1.0, "feature2": "category_a", "id": "patient_1"},
  {"feature1": 2.0, "feature2": "category_b", "id": "patient_2"}
]
```

### Output Format
Your model should return JSON results:
```json
[
  {"prediction": 0.85, "confidence": 0.92, "id": "patient_1"},
  {"prediction": 0.73, "confidence": 0.88, "id": "patient_2"}
]
```

## Troubleshooting

### Build Errors
1. **Python package conflicts**: Check `pyproject.toml` versions
2. **R package missing**: Add to `DESCRIPTION` file
3. **File not found**: Check COPY paths in Dockerfile

### Registration Errors
1. **"Examples required"**: Add `examples.json` or provide via API
2. **"README required"**: Add `README.md` or provide via API  
3. **"Image not found"**: Build your Docker image first

### Runtime Errors
1. **Permission denied**: Make sure `predict` script is executable
2. **Module not found**: Check your dependencies are installed
3. **File paths**: Use relative paths from `/app` directory

### Common Dockerfile Mistakes
```dockerfile
# ❌ WRONG - breaks model server integration
CMD ["python", "predict.py"]
ENTRYPOINT ["./predict"]

# ✅ CORRECT - let model server handle execution
# (no CMD/ENTRYPOINT)
```

Use the validator to catch these:
```bash
python validate-dockerfile.py Dockerfile
```

## Advanced Topics

### Custom Base Images
You can use custom base images, but ensure they:
- Have Python 3.11+ or R 4.0+
- Include basic JSON parsing libraries
- Don't set CMD/ENTRYPOINT

### Model Versioning
Use image tags for model versions:
```bash
docker build -t my-model:v1.0 .
docker build -t my-model:v1.1 .
```

### Large Models
For large model files:
1. Use `.dockerignore` to exclude unnecessary files
2. Consider model registries for sharing artifacts
3. Use multi-stage builds if needed

### GPU Models
For GPU-enabled models:
1. Use appropriate base images (`nvidia/cuda`)
2. Install GPU-specific libraries
3. Test with GPU-enabled Docker runtime

## Examples

See the `examples/` directory for complete working examples:
- `examples/simple-classifier/` - Basic scikit-learn model
- `examples/deep-learning/` - PyTorch model example
- `examples/r-regression/` - R linear model example
