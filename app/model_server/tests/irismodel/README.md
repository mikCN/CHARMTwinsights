# Example model docker image

This directory contains resources to build an example model docker image for uploading to CHARMTwinsight. 
A compatible docker image MUST:

- Use `/app` as the default working directory (set via `WORKDIR /app` in the Dockerfile), containing:
  - A `README.md`
  - An executable `predict`
      - `predict` must take a single file input as its first argument, which must be a `json`-formatted *list* (to support batches of predictions)
  - An `examples.json`
      - This must be a `json`-formatted list, providing an example batch of inputs
- `predict` should succeed when running `predict examples.json` and print (on standard output) a `json`-formatted list (corresponding to the batch of predictions).

**Note**: This example includes the model building in the docker container, but not as part of the docker build. It
is perfectly valid to train a model on an external system, export it (e.g. with `saveRDS()` in R or `mlflow` in Python as shown here), copy it into the docker image, and have `predict` load and use it.

Without being overly prescriptive, the `README.md` should provide relevant information about the model,
including authorship, contact information, and a description or other documentation necessary for 
effective use of the model. An example is provided below.

# Iris Model

**Author:** Shawn O'Neil  
**Description:** A logistic regression classifier for the Iris dataset.  
**Framework:** scikit-learn  
**Contact:** shawn@tislab.org

## Details

This is an example model trained on the classical Iris dataset to predict species (encoded as `0` for setosa, 
`1` for versicolor, and `2` for virginica). It was trained with a 75%/25% train/test split, using 200 max iterations
of Scikit-Learn's LogisticRegression classifier.

## Example Input

```json
[
  {
    "sepal length (cm)": 5.1,
    "sepal width (cm)": 3.5,
    "petal length (cm)": 1.4,
    "petal width (cm)": 0.2
  },
  {
    "sepal length (cm)": 7.0,
    "sepal width (cm)": 3.2,
    "petal length (cm)": 4.7,
    "petal width (cm)": 1.4
  }
]
```

## Example Output
```json
[0, 2]
```

