# Fermento – Backend Architecture (v1)

## Core principle
**Single source of truth = API + DB**  
Everything else either **writes to it**, **reads from it**, or **derives from it**.  
MQTT is **device-facing only**.

---

## Services

### API (System of Record)
**Responsibility**
- Owns the database
- CRUD for domain resources:
  - `starter`, `jar`, `flour`, `flour_blend`
  - `feeding_event`, `feeding_sample`
  - derived data + predictions
- Enforces schema, authentication, and consistency

**Protocols**
- HTTP / REST  
- Database driver (internal only)

---

### Ingestor (Write-only entry point)
**Responsibility**
- Receives incoming data from:
  - devices (sensor samples)
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

### Data Processor
**Responsibility**
- Reads raw samples from the API
- Computes derived metrics / features:
  - smoothing
  - growth rate
  - feature vectors
- Writes derived data back to the API

**Protocols**
- HTTP ↔ API

---

### Predictor
**Responsibility**
- Reads features and context from the API
- Runs prediction models
- Produces peak time / ETA / confidence
- Writes predictions to the API

**Protocols**
- HTTP ↔ API

---

### Notifier
**Responsibility**
- Detects notification conditions:
  - peak soon
  - peak now
  - anomalies
- Sends notifications to phones
- No influence on the core data model

**Protocols**
- HTTP (read from API or triggered)
- HTTP → push providers (FCM / APNS / etc.)

---

## Device interaction

### Write path