# Fermento – Backend Architecture (v1)

## Core Principle
**Single source of truth = API + Database**

All data is:
- **written to** the API,
- **read from** the API,
- or **derived** from data in the API.

Devices never talk to the database directly.  
MQTT is **device-facing only**.

---

## Services Overview

### 1) API (System of Record)
**Responsibility**
- Owns the database
- CRUD for domain resources:
  - `starter`
  - `jar`
  - `flour`
  - `flour_blend`
  - `feeding_event`
  - `feeding_sample`
  - derived data and predictions
- Enforces schema, authentication, authorization, and consistency
- Acts as the provider abstraction layer (Airtable today, SQL later)

**Protocols**
- HTTP / REST  
- Database driver (internal only)

---

### 2) Ingestor (Write-only)
**Responsibility**
- Receives incoming data from:
  - devices (sensor telemetry)
  - data processor (derived data)
  - predictor (predictions)
- Validates payloads
- Deduplicates using `msg_id`
- Writes data to the API
- **Never reads from the API**
- No business logic

**Protocols**
- MQTT or HTTP (inputs)
- HTTP → API (writes)

---

### 3) Data Processor
**Responsibility**
- Reads raw samples from the API
- Computes derived metrics and features:
  - smoothing
  - growth rate
  - feature vectors
- Writes derived data back to the API

**Protocols**
- HTTP ↔ API

---

### 4) Predictor
**Responsibility**
- Reads features and context from the API
- Runs prediction models
- Produces:
  - peak timestamp
  - ETA to peak
  - confidence
  - model version
- Writes predictions to the API

**Protocols**
- HTTP ↔ API

---

### 5) Notifier
**Responsibility**
- Detects notification conditions:
  - peak soon
  - peak now
  - anomalies
- Sends notifications to phones
- Does not affect core data models

**Protocols**
- HTTP (read from API or triggered)
- HTTP → push providers (FCM / APNS / email / SMS)

---

## Device Interaction

**Write path**. 
Device → MQTT or HTTP → Ingestor → HTTP → API → Database

**Read path**
- Devices retrieve reference data (feeding events, flour blends, predictions) in one of two ways:
  - **Directly via HTTP** from the API (simplest)
  - **Via MQTT** from a read-only Query / Cache service that reads from the API and publishes retained topics for the device UI (better UX, push-based)

The Query / Cache service is optional, read-only, and contains no business logic.

---

## Clear Boundaries (Rules)
- **Only the API talks to the database**
- **Ingestor only writes**
- **Data Processor and Predictor read → compute → write**
- **Devices never touch the database**
- **MQTT is for devices**
- **HTTP is for backend services**

---

## Mental Model
> Data flows in through the ingestor, is refined by processors, predicted by the predictor, stored by the API, and optionally pushed to humans or devices.