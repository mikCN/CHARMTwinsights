from fastapi import FastAPI
import pandas as pd
from fhiry.fhirsearch import Fhirsearch

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from the pyserver!"}


@app.get("/patients")
def get_patients():

    # example based on https://github.com/dermatologist/fhiry
    fs = Fhirsearch(fhir_base_url = "http://hapi:8080/fhir")

    # my_fhir_search_parameters = {
    #     #"code": "http://snomed.info/sct|39065001",
    # }

    # df = fs.search(resource_type = "Patient", search_parameters = my_fhir_search_parameters)

    df = fs.search()

    print(df.info())

    return df



if __name__ == "__main__":
    import uvicorn
    get_patients()
    uvicorn.run(app, host="0.0.0.0", port=8000)

