<template>
  <div style="max-width: 700px; margin: 2rem auto; font-family: sans-serif;">
    <h1>CHARMTwinsight Demo UI</h1>
    
    <!-- Generate Synthetic Patients -->
    <section style="margin-bottom: 2em;">
      <h2>Generate Synthetic Patients</h2>
      <label>
        Number of Patients:
        <input v-model.number="numPatients" type="number" min="1" style="width: 80px;" />
      </label>
      <label style="margin-left: 1em;">
        Years of History:
        <input v-model.number="numYears" type="number" min="1" style="width: 60px;" />
      </label>
      <label style="margin-left: 1em;">
        Cohort ID:
        <input v-model="cohortId" style="width: 120px;" />
      </label>
      <button :disabled="loading" @click="generatePatients" style="margin-left: 1em;">
        {{ loading ? "Generating..." : "Generate" }}
      </button>
      <div v-if="genResponse" style="margin-top: 1em;">
        <strong>Response:</strong>
        <pre>{{ genResponse }}</pre>
      </div>
    </section>
    
<section>
  <h2>List Patients</h2>
  <button :disabled="loadingPatients" @click="listPatients">
    {{ loadingPatients ? "Loading..." : "List Patients" }}
  </button>
  <div v-if="patientsRaw" style="margin-top: 1em;">
    <details open>
      <summary>Raw Response JSON</summary>
      <pre>{{ patientsRaw }}</pre>
    </details>
  </div>
  <div v-if="patientsError" style="color: red;">{{ patientsError }}</div>
</section>

<section>
  <h2>Get Patient $everything</h2>
  <label>
    Patient ID:
    <input v-model="everythingId" placeholder="Enter patient_id" style="width: 220px;" />
  </label>
  <button :disabled="loadingEverything || !everythingId" @click="getEverything" style="margin-left: 1em;">
    {{ loadingEverything ? "Loading..." : "Show $everything" }}
  </button>
  <div v-if="everythingRaw" style="margin-top: 1em;">
    <details open>
      <summary>Raw $everything Response</summary>
      <pre>{{ everythingRaw }}</pre>
    </details>
  </div>
  <div v-if="everythingError" style="color: red;">{{ everythingError }}</div>
</section>



    <!-- Patient Details -->
    <section v-if="selectedPatient">
      <h2>Patient Details ($everything)</h2>
      <p><strong>Patient ID:</strong> {{ selectedPatientId }}</p>
      <div v-if="patientLoading">Loading patient details...</div>
      <div v-if="patientError" style="color: red;">{{ patientError }}</div>
      <pre v-if="patientDetails">{{ patientDetails }}</pre>
      <button @click="clearPatient" style="margin-top: 1em;">Close</button>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000"

const numPatients = ref(10)
const numYears = ref(1)
const cohortId = ref('testcohort')
const loading = ref(false)
const genResponse = ref('')

const loadingPatients = ref(false)
const patients = ref([])
const patientsError = ref('')

const selectedPatient = ref(null)
const selectedPatientId = ref('')
const patientLoading = ref(false)
const patientError = ref('')
const patientDetails = ref('')

async function generatePatients() {
  loading.value = true
  genResponse.value = ""
  try {
    const url = `${API_BASE}/synthetic/synthea/generate-synthetic-patients?num_patients=${numPatients.value}&num_years=${numYears.value}&cohort_id=${encodeURIComponent(cohortId.value)}`
    const resp = await axios.post(url)
    genResponse.value = JSON.stringify(resp.data, null, 2)
  } catch (e) {
    genResponse.value = "Error: " + (e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

const patientsRaw = ref('')

async function listPatients() {
  loadingPatients.value = true
  patientsRaw.value = ''
  patientsError.value = ''
  try {
    const resp = await axios.get(`${API_BASE}/synthetic/synthea/list-all-patients`)
    // Store the prettified JSON string
    patientsRaw.value = JSON.stringify(resp.data, null, 2)
  } catch (e) {
    patientsError.value = "Error: " + (e?.response?.data?.detail || e.message)
  } finally {
    loadingPatients.value = false
  }
}


async function showPatient(id) {
  selectedPatient.value = null
  selectedPatientId.value = id
  patientLoading.value = true
  patientError.value = ''
  patientDetails.value = ''
  try {
    // You can add query params as needed (e.g. start, end, _type, etc)
    const resp = await axios.get(`${API_BASE}/stats/patients/${encodeURIComponent(id)}/$everything`)
    patientDetails.value = JSON.stringify(resp.data, null, 2)
    selectedPatient.value = resp.data
  } catch (e) {
    patientError.value = "Error: " + (e?.response?.data?.detail || e.message)
  } finally {
    patientLoading.value = false
  }
}

function clearPatient() {
  selectedPatient.value = null
  selectedPatientId.value = ''
  patientDetails.value = ''
  patientError.value = ''
}


const everythingId = ref('')
const everythingRaw = ref('')
const loadingEverything = ref(false)
const everythingError = ref('')

async function getEverything() {
  loadingEverything.value = true
  everythingRaw.value = ''
  everythingError.value = ''
  try {
    const url = `${API_BASE}/stats/patients/${encodeURIComponent(everythingId.value)}/$everything`
    const resp = await axios.get(url)
    everythingRaw.value = JSON.stringify(resp.data, null, 2)
  } catch (e) {
    everythingError.value = "Error: " + (e?.response?.data?.detail || e.message)
  } finally {
    loadingEverything.value = false
  }
}

</script>
