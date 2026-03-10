# IAES — Industrial Asset Event Standard v1.2

> A vendor-neutral event format for industrial asset intelligence.

## Purpose

IAES defines how industrial asset signals, diagnoses, and maintenance intents are represented and transferred across heterogeneous operational systems.

IAES is NOT a product. It is a data contract. Any system — sensor platform, AI engine, CMMS, historian, or dashboard — can produce or consume IAES events without knowing the implementation details of the other side.

## Principles

1. **Vendor neutrality** — No dependency on SAP, PI System, Odoo, or any specific vendor.
2. **Legacy compatibility** — Events map cleanly to CMMS, historians, SCADA, and IoT platforms.
3. **Event-oriented** — Each object represents something that happened (measurement, diagnosis, intent).
4. **Complete traceability** — Every event traces back to its origin via `event_id`, `correlation_id`, `source_event_id`.
5. **Extensibility** — The `data` payload and `metadata` field allow new fields without breaking consumers.

## Terminology

| Term | Definition |
|------|-----------|
| **Event** | A self-contained JSON object describing something that happened to an industrial asset. |
| **Producer** | Any system that creates IAES events — sensor gateways, AI engines, rule engines, human inspectors, SCADA systems. |
| **Consumer** | Any system that receives and acts on IAES events — CMMS, historians, dashboards, digital twin platforms. |
| **Envelope** | The common wrapper fields shared by all IAES events (spec_version, event_type, event_id, etc.). |
| **Correlation** | A group of related events sharing the same `correlation_id`, representing a single observation-to-action flow. |
| **Source** | A dot-notation string identifying the producer of an event (e.g. `wertek.ai.vibration`, `operator.field_assessment`). |
| **Intent** | A declaration that an action should be considered, without prescribing how the consumer should act. Used in `maintenance.work_order_intent`. |
| **Health Index** | A normalized 0-1 score representing asset condition (0 = failed, 1 = healthy). |
| **RUL** | Remaining Useful Life — estimated days until the asset requires intervention. |

## Common Envelope

Every IAES event shares this envelope:

```json
{
  "spec_version": "1.2",
  "event_type": "asset.health",
  "event_id": "uuid",
  "correlation_id": "uuid",
  "source_event_id": "uuid | null",
  "batch_id": "string | null",
  "timestamp": "ISO 8601",
  "source": "vendor.system.subsystem",
  "content_hash": "sha256_16char",
  "asset": {
    "asset_id": "string",
    "asset_name": "string | null",
    "plant": "string | null",
    "area": "string | null"
  },
  "data": {}
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `spec_version` | string | yes | IAES spec version (`"1.0"`, `"1.1"`, or `"1.2"`) |
| `event_type` | string | yes | Dot-notation event type |
| `event_id` | UUID | yes | Unique identifier for this event |
| `correlation_id` | UUID | yes | Groups related events in a single flow |
| `source_event_id` | UUID | no | References the originating event |
| `timestamp` | ISO 8601 | yes | When the event occurred |
| `source` | string | yes | Dot-notation producer identity (e.g. `wertek.ai.diagnosis`, `operator.manual_inspection`) |
| `batch_id` | string | no | Groups events from a single batch operation (e.g. gateway poll, bulk sync) |
| `content_hash` | string | no | SHA-256 prefix (16 chars) of `data` payload for dedup |
| `asset` | object | yes | Asset identity (see Asset Identity) |
| `data` | object | yes | Event-specific payload |

### Asset Identity

```json
{
  "asset_id": "MOTOR-001",
  "asset_name": "Motor Bomba P-101",
  "plant": "Pesqueria",
  "area": "Turbinas"
}
```

The standard deliberately does NOT define a full asset hierarchy. Different organizations model hierarchies differently (ISO 14224, ISA-95, custom). IAES only requires enough context to identify the asset.

## Event Types

### `asset.measurement`

A physical sensor reading.

```json
{
  "event_type": "asset.measurement",
  "data": {
    "measurement_type": "vibration_rms",
    "value": 4.2,
    "unit": "mm/s",
    "sensor_id": "SENSOR-045",
    "location": "bearing_drive_end"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `measurement_type` | string | yes | Type (vibration_velocity, temperature, current, etc.) |
| `value` | number | yes | Numeric value |
| `unit` | string | yes | Engineering unit |
| `sensor_id` | string | no | Physical sensor identifier |
| `location` | string | no | Measurement point on the asset |
| `units_qualifier` | string | no | Signal processing method: `rms`, `peak`, `peak_to_peak`, `average`, `true_rms` (ISO 17359 §6.3, v1.2) |
| `sampling_rate_hz` | number | no | Sampling rate in Hz (v1.2) |
| `acquisition_duration_s` | number | no | Measurement acquisition window in seconds (v1.2) |

### `asset.health`

AI diagnosis / health state change. Includes recommended action.

```json
{
  "event_type": "asset.health",
  "data": {
    "health_index": 0.16,
    "anomaly_score": 0.92,
    "severity": "critical",
    "failure_mode": "bearing_inner_race",
    "fault_confidence": 0.87,
    "rul_days": 5,
    "recommended_action": "Replace bearing immediately",
    "estimated_downtime_hours": 4
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `health_index` | float 0-1 | yes | Normalized health (0 = failed, 1 = healthy) |
| `anomaly_score` | float 0-1 | no | Probability of anomaly |
| `severity` | enum | yes | info, low, medium, high, critical |
| `failure_mode` | string | no | Classified fault type |
| `fault_confidence` | float 0-1 | no | Classification confidence |
| `rul_days` | integer | no | Remaining Useful Life in days |
| `recommended_action` | string | no | Human-readable action suggestion |
| `estimated_downtime_hours` | float | no | Estimated repair duration |
| `iso_13374_status` | string | no | ISO 13374-2 health status: `unknown`, `normal`, `satisfactory`, `unsatisfactory`, `unacceptable`, `imminent_failure`, `failed` (v1.2, see Appendix C) |
| `iso_14224` | object | no | ISO 14224 failure classification codes (v1.2, see Appendix B) |

### `maintenance.work_order_intent`

Declares the INTENT to create a work order. The consumer decides whether and how to act.

```json
{
  "event_type": "maintenance.work_order_intent",
  "data": {
    "title": "Bearing failure predicted",
    "description": "Inner race defect detected by AI diagnosis",
    "priority": "critical",
    "recommended_due_days": 3,
    "triggered_by": "alert"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Work order title |
| `description` | string | no | Detailed description |
| `priority` | enum | yes | low, medium, high, emergency |
| `recommended_due_days` | integer | no | Suggested deadline in days |
| `triggered_by` | string | no | What caused this intent: `alert`, `schedule`, `manual`, `threshold`, `ai_diagnosis` |

> **Note: severity vs priority.** `severity` (on `asset.health`) describes the *condition* of the asset. `priority` (on `maintenance.work_order_intent`) describes the *urgency of response*. They are related but distinct: a critical severity typically maps to emergency priority, but the consumer decides this mapping.

### `maintenance.completion` (v1.1)

Acknowledges the completion of a work order. Links back to the original intent via `correlation_id`.

```json
{
  "event_type": "maintenance.completion",
  "data": {
    "status": "completed",
    "work_order_id": "WO-2026-0042",
    "actual_duration_seconds": 7200,
    "technician_id": "TECH-003",
    "checklist_completion_pct": 100,
    "completion_notes": "Bearing replaced. Post-repair vibration 0.8 mm/s.",
    "spare_parts_count": 1,
    "failure_confirmed": true,
    "failure_mode": "bearing_inner_race"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | enum | yes | completed, partially_completed, cancelled, deferred |
| `work_order_id` | string | yes | Identifier of the completed work order |
| `actual_duration_seconds` | integer | no | Actual time spent in seconds |
| `technician_id` | string | no | Identifier of the technician |
| `checklist_completion_pct` | float 0-100 | no | Percentage of checklist completed |
| `completion_notes` | string | no | Free-text notes from the technician |
| `spare_parts_count` | integer | no | Number of spare parts consumed (detail in `spare_part_usage` events) |
| `failure_confirmed` | boolean | no | Whether the predicted failure mode was confirmed |
| `failure_mode` | string | no | Confirmed or observed failure mode (see Appendix A) |
| `iso_14224` | object | no | ISO 14224 failure classification codes confirmed during maintenance (v1.2, see Appendix B) |

### `asset.hierarchy` (v1.1)

Synchronizes asset hierarchy structure across systems. Each event represents one node and its relationship.

```json
{
  "event_type": "asset.hierarchy",
  "data": {
    "hierarchy_level": "equipment",
    "relationship_type": "child_of",
    "parent_asset_id": "AREA-TURBINAS",
    "asset_type": "motor",
    "serial_number": "WEG-2024-78432",
    "manufacturer": "WEG",
    "model": "W22 Premium 75HP",
    "is_active": true
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `hierarchy_level` | enum | yes | organization, plant, area, equipment |
| `relationship_type` | enum | yes | parent_of, child_of, sibling_of, depends_on |
| `parent_asset_id` | string | no | Identifier of the parent node |
| `asset_type` | string | no | Equipment type (motor, pump, compressor, etc.) |
| `serial_number` | string | no | Manufacturer serial number |
| `manufacturer` | string | no | Equipment manufacturer |
| `model` | string | no | Equipment model |
| `location` | string | no | Physical location description |
| `is_active` | boolean | no | Whether the asset is active/operational |

### `sensor.registration` (v1.1)

Sensor discovery, onboarding, and lifecycle tracking.

```json
{
  "event_type": "sensor.registration",
  "data": {
    "sensor_id": "MCSA-T41-001",
    "registration_status": "registered",
    "sensor_model": "Wertek MCSA CT Module",
    "device_serial": "T41-2026-00042",
    "firmware_version": "1.0.3",
    "measurement_capabilities": ["current_waveform", "current_spectrum", "current_rms", "thd"],
    "calibration_date": "2026-03-05",
    "communication_protocol": "mqtt"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sensor_id` | string | yes | Unique sensor identifier |
| `registration_status` | enum | yes | discovered, registered, calibrated, decommissioned |
| `sensor_model` | string | no | Sensor hardware model |
| `device_serial` | string | no | Device serial number |
| `firmware_version` | string | no | Current firmware version |
| `measurement_capabilities` | string[] | no | Measurement types this sensor provides |
| `calibration_date` | ISO 8601 date | no | Last calibration date |
| `communication_protocol` | string | no | Protocol (mqtt, modbus_tcp, opcua, lorawan, etc.) |

### `maintenance.spare_part_usage` (v1.1)

Records spare parts consumed during a maintenance activity. Linked to the work order via `work_order_id` and to the completion event via `correlation_id`. There may be 0-N spare part usage events per work order.

```json
{
  "event_type": "maintenance.spare_part_usage",
  "data": {
    "work_order_id": "WO-2026-0042",
    "spare_part_id": "SP-SKF-6205",
    "quantity_used": 1,
    "part_number": "SKF 6205-2RS",
    "part_name": "Rodamiento rigido de bolas 6205-2RS",
    "unit_cost": 28.50,
    "currency": "USD",
    "total_cost": 28.50
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `work_order_id` | string | yes | Work order that consumed the part |
| `spare_part_id` | string | yes | Part identifier in the inventory system |
| `quantity_used` | number | yes | Quantity consumed (> 0) |
| `part_number` | string | no | Manufacturer part number |
| `part_name` | string | no | Human-readable part name |
| `unit_cost` | number | no | Cost per unit |
| `currency` | string | no | ISO 4217 currency code (USD, MXN, BRL) |
| `total_cost` | number | no | Total cost (quantity_used * unit_cost) |

## Severity Standard

IAES defines five severity levels:

| Level | Meaning |
|-------|---------|
| `info` | Informational, no action needed |
| `low` | Minor, schedule for next planned maintenance |
| `medium` | Moderate, plan intervention within weeks |
| `high` | Significant, plan intervention within days |
| `critical` | Immediate action required |

## Idempotency

Every event includes:
- `event_id` — unique, never reused
- `content_hash` — SHA-256 of the `data` payload (16-char prefix)
- `correlation_id` — groups related events in a flow

Consumers SHOULD use `content_hash` + `asset.asset_id` + `event_type` to detect duplicate events.

## Producers

IAES events are produced by systems capable of interpreting operational signals — not by the signals themselves.

A PLC, sensor, or gateway knows `vibration_rms = 4.6`. That is telemetry, not a diagnosis. IAES begins where interpretation begins: an AI model that classifies a bearing fault, a rule engine that triggers on a threshold, or a technician who hears cavitation.

### Intelligence layer producers

| Source | Example `source` value | Typical events |
|--------|----------------------|----------------|
| AI diagnosis engine | `wertek.ai.vibration` | `asset.health` |
| Rule/threshold engine | `acme.rule_engine` | `asset.health` |
| Manual inspection | `operator.manual_inspection` | `asset.health`, `asset.measurement` |
| Technician assessment | `operator.field_assessment` | `asset.health` |
| Lab analysis | `lab.oil_analysis` | `asset.measurement` |
| Maintenance application | `wertek.ai.cmms` | `maintenance.work_order_intent` |

### Signal sources (upstream of IAES)

Operational systems such as PLCs, SCADA platforms, sensor gateways, and historians typically emit raw signals or measurements. These are converted into IAES events by downstream intelligence layers.

```
Industrial Signals              IAES Events
(PLC / Sensors / SCADA)         (semantic, interpreted)
        │                               │
        ▼                               ▼
  Telemetry Layer               ┌──────────────┐
  (OPC UA / Modbus / MQTT)      │  CMMS        │
        │                       │  Dashboards   │
        ▼                       │  Historians   │
  Intelligence Layer     ──────>│  Integrations │
  (AI / rules / human)         └──────────────┘
```

An edge device MAY produce IAES events directly if it has sufficient intelligence (e.g. edge AI, embedded rule engine). But the typical flow is: signals are ingested by an intelligence layer, which then emits IAES events.

The `source` field is what makes IAES vendor-neutral. A technician with a stethoscope and an AI model both produce the same `asset.health` event — the consumer doesn't need to know the difference.

## Producer Guidelines

Systems that emit IAES events MUST follow these rules:

### Required behavior

1. **Set all required envelope fields.** Every event MUST include `spec_version`, `event_type`, `event_id`, `correlation_id`, `timestamp`, `source`, `asset` (with at least `asset_id`), and `data`.

2. **Generate unique `event_id` values.** Each event MUST have a globally unique `event_id` (UUID v4 recommended). Never reuse an `event_id` across events.

3. **Use dot-notation for `source`.** The `source` field MUST follow the pattern `vendor.system[.subsystem]`. Examples: `wertek.ai.vibration`, `banner.dxm100`, `operator.manual_inspection`. Use lowercase, alphanumeric characters, dots, and underscores only.

4. **Use ISO 8601 for timestamps.** The `timestamp` field MUST be in UTC with timezone designator (e.g. `2026-03-06T17:50:17Z`).

5. **Do not assume consumer behavior.** A `maintenance.work_order_intent` declares intent — the producer MUST NOT assume the consumer will create a work order, or create it in any specific format.

### Recommended behavior

1. **Set `correlation_id` to group related events.** When a measurement triggers a diagnosis that triggers a work order intent, all three events SHOULD share the same `correlation_id`.

2. **Set `source_event_id` for causal chains.** When an event is caused by another event (e.g. a health assessment caused by a measurement), set `source_event_id` to the `event_id` of the cause.

3. **Compute `content_hash` for deduplication.** Producers SHOULD compute `content_hash` as the first 16 characters of the SHA-256 hex digest of the serialized `data` payload (canonical JSON, sorted keys).

4. **Include `asset_name`, `plant`, and `area` when available.** These fields are optional but significantly improve human readability in logs, dashboards, and audit trails.

5. **Use standard `failure_mode` values when possible.** Common values: `bearing_inner_race`, `bearing_outer_race`, `misalignment`, `unbalance`, `looseness`, `cavitation`, `overheating`, `electrical_fault`. Custom values are allowed.

## Consumer Guidelines

Systems that receive IAES events MUST follow these rules:

### Required behavior

1. **Tolerate unknown fields.** Consumers MUST ignore fields in `data` that they do not recognize. Never reject an event because it contains extra fields. This is essential for forward compatibility.

2. **Tolerate unknown `event_type` values.** If a consumer receives an event with an `event_type` it does not support (e.g. a future `asset.hierarchy`), it MUST NOT error. It MAY log the event and skip processing.

3. **Validate `spec_version`.** Consumers SHOULD check `spec_version` and MAY reject events from unsupported major versions.

### Recommended behavior

1. **Deduplicate using `content_hash`.** Consumers SHOULD detect duplicate events using the combination of `content_hash` + `asset.asset_id` + `event_type`. If `content_hash` is not present, fall back to `event_id` uniqueness.

2. **Use `correlation_id` to reconstruct flows.** Consumers that display or analyze event chains SHOULD group events by `correlation_id` and order them by `timestamp`.

3. **Use `source_event_id` for traceability.** When displaying a work order intent, consumers SHOULD link back to the health event that triggered it (via `source_event_id`).

4. **Map severity to native priority.** Consumers that create native objects (work orders, notifications) SHOULD map IAES severity levels to their native priority system. A suggested default mapping:

| IAES severity | SAP PM | MaintainX | Odoo | General |
|---------------|--------|-----------|------|---------|
| `info` | — (no action) | — | — | — |
| `low` | Priority 4 | LOW | 0 (Very Urgent: No) | Low |
| `medium` | Priority 3 | MEDIUM | 1 (Normal) | Medium |
| `high` | Priority 2 | HIGH | 2 (Urgent) | High |
| `critical` | Priority 1 | HIGH | 3 (Very Urgent) | Critical |

5. **Respect intent semantics.** A `maintenance.work_order_intent` is a suggestion, not a command. Consumers MAY apply filters, rules, or approval workflows before creating native work orders. The consumer is the authority on what gets created in its system.

## Typical Flow

```
Observation (sensor, AI, or human expert)
    |
    v
asset.measurement ─── [batch_id groups gateway polls]
    |
    v
Diagnosis (AI engine, rule engine, or expert assessment)
    |
    v
asset.health
    |
    v
maintenance.work_order_intent
    |
    v
Connector Adapter (SAP / Odoo / MaintainX / Fracttal / PI System)
    |
    v
maintenance.completion ─── [technician closes WO]
    |
    v
maintenance.spare_part_usage ─── [0-N parts consumed]
```

All events in the chain share the same `correlation_id`. Each references its predecessor via `source_event_id`.

## System Compatibility

| System | IAES Mapping |
|--------|-------------|
| SAP PM | Maintenance Notification / Order |
| PI System | Tag value writes |
| AVEVA Data Hub | SDS Stream writes |
| Odoo | maintenance.request |
| MaintainX | User Variables |
| Fracttal | Custom fields + OT |
| Grafana | Dashboard metrics |
| Any MQTT broker | JSON payload |

## Versioning

IAES uses semantic versioning for the specification itself:

- **`spec_version`** in every event envelope identifies which version of the spec was used to produce it.
- **Minor versions** (1.1, 1.2) add new optional fields, new event types, or new `triggered_by` values. They never remove existing fields or change required fields. Consumers built for 1.0 SHOULD accept events from 1.x without error.
- **Major versions** (2.0) may introduce breaking changes: removing fields, changing required fields, renaming event types, or changing envelope structure. Consumers MAY reject events from unsupported major versions.
- **Producers** MUST set `spec_version` to the version they implement.
- **Consumers** SHOULD accept events where the major version matches, even if the minor version is higher than what they support.

### Version history

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | March 2026 | Initial release. 3 event types, common envelope, JSON Schema. |
| 1.1 | March 2026 | 4 new event types (maintenance.completion, asset.hierarchy, sensor.registration, maintenance.spare_part_usage), batch_id envelope field, failure mode taxonomy (Appendix A). |
| 1.2 | March 2026 | ISO alignment: `units_qualifier`, `sampling_rate_hz`, `acquisition_duration_s` on asset.measurement (ISO 17359); `iso_13374_status` on asset.health (ISO 13374); `iso_14224` object on asset.health + maintenance.completion (ISO 14224). All new fields optional — full backward compatibility. Appendix B (ISO 14224 codes), Appendix C (ISO 13374 mapping). |

## Appendix A: Failure Mode Taxonomy

Standard failure mode values for use in `asset.health` and `maintenance.completion` events. Based on ISO 14224 failure mode classification. Custom values are allowed — this list provides interoperability defaults.

### Rotating Equipment

| Value | Description |
|-------|-------------|
| `bearing_inner_race` | Inner race defect |
| `bearing_outer_race` | Outer race defect |
| `bearing_ball` | Rolling element defect |
| `bearing_cage` | Cage/retainer defect |
| `misalignment` | Shaft misalignment (angular or parallel) |
| `unbalance` | Mass unbalance |
| `looseness_mechanical` | Mechanical looseness (structural or rotating) |
| `looseness_electrical` | Electrical looseness (connections) |
| `gear_mesh` | Gear mesh defect |
| `gear_tooth` | Gear tooth wear or breakage |

### Electrical

| Value | Description |
|-------|-------------|
| `electrical_fault` | General electrical fault |
| `winding_short` | Stator or rotor winding short circuit |
| `broken_rotor_bar` | Broken rotor bar (induction motors) |
| `eccentricity` | Air gap eccentricity (static or dynamic) |

### Fluid / Thermal

| Value | Description |
|-------|-------------|
| `cavitation` | Cavitation in pumps or valves |
| `overheating` | Abnormal temperature rise |
| `lubrication_failure` | Inadequate or degraded lubrication |
| `seal_leak` | Seal or gasket leak |
| `fouling` | Surface fouling or buildup |
| `corrosion` | Corrosion or material degradation |

Producers SHOULD use these values when applicable. Custom values (e.g. `blade_erosion`, `coupling_wear`) are valid and consumers MUST tolerate them.

## Appendix B: ISO 14224 Failure Classification Codes

Optional structured failure coding for use in the `iso_14224` object on `asset.health` and `maintenance.completion` events. Based on ISO 14224:2016 failure classification.

### Object Structure

```json
{
  "iso_14224": {
    "mechanism_code": "1.1",
    "mechanism_label": "Mechanical wear",
    "cause_code": "4",
    "cause_label": "Operations/Maintenance",
    "detection_method": "2",
    "detection_label": "Condition monitoring"
  }
}
```

All fields are optional. Producers MAY include any subset.

### Failure Mechanism Codes

| Code | Mechanism | Related IAES failure_mode |
|------|-----------|--------------------------|
| 1.1 | Mechanical wear | `bearing_inner_race`, `bearing_outer_race`, `gear_tooth` |
| 1.2 | Fatigue | `bearing_ball`, `bearing_cage` |
| 1.3 | Corrosion | `corrosion` |
| 1.4 | Erosion | `cavitation` |
| 2.1 | Overheating | `overheating` |
| 2.2 | Electrical breakdown | `electrical_fault`, `winding_short` |
| 3.1 | Vibration-induced | `unbalance`, `misalignment`, `looseness_mechanical` |
| 3.2 | Leakage | `seal_leak` |
| 4.1 | Contamination | `fouling`, `lubrication_failure` |

### Failure Cause Codes

| Code | Cause Category |
|------|---------------|
| 1 | Design-related |
| 2 | Fabrication / Manufacturing |
| 3 | Installation |
| 4 | Operations / Maintenance |
| 5 | Management / Organization |
| 6 | Miscellaneous / Unknown |

### Detection Method Codes

| Code | Method | Typical IAES `source` |
|------|--------|-----------------------|
| 1 | Periodic maintenance | `operator.manual_inspection` |
| 2 | Condition monitoring | `wertek.ai.vibration`, `wertek.ai.diagnosis` |
| 3 | Functional testing | `operator.field_assessment` |
| 4 | Casual observation | `operator.manual_inspection` |
| 5 | On demand / Breakdown | — (reactive) |

The `iso_14224` object coexists with the `failure_mode` field from Appendix A. `failure_mode` provides a quick human-readable label; `iso_14224` provides structured classification for interoperability with systems that use ISO 14224 coding (common in oil & gas, power generation, and ISO-certified plants).

## Appendix C: ISO 13374 Health Status Mapping

The `iso_13374_status` field on `asset.health` carries the ISO 13374-2 health status level. This is **complementary** to the IAES `severity` field:

- **`severity`** is ACTION-oriented: what should we DO about this? (info → critical)
- **`iso_13374_status`** is CONDITION-oriented: what IS the current state? (unknown → failed)

### Status Levels

| ISO 13374 Status | Description | Nearest IAES `severity` |
|------------------|-------------|------------------------|
| `unknown` | Insufficient data to determine condition | `info` |
| `normal` | Operating within normal parameters | `info` |
| `satisfactory` | Minor deviations, still acceptable | `low` |
| `unsatisfactory` | Noticeable deviation from normal | `medium` |
| `unacceptable` | Exceeds acceptable operating limits | `high` |
| `imminent_failure` | Failure expected in near term | `critical` |
| `failed` | Asset has failed or is non-functional | `critical` |

### Usage Example

```json
{
  "event_type": "asset.health",
  "data": {
    "health_index": 0.16,
    "severity": "critical",
    "iso_13374_status": "imminent_failure",
    "failure_mode": "bearing_inner_race",
    "rul_days": 5,
    "iso_14224": {
      "mechanism_code": "1.1",
      "mechanism_label": "Mechanical wear",
      "detection_method": "2",
      "detection_label": "Condition monitoring"
    }
  }
}
```

Consumers that understand ISO 13374 can use `iso_13374_status` for condition-based reporting. Others use `severity` for action-based alerting. Both fields are optional; when both are present, they provide complementary perspectives.

### ISO 13374 6-Block Processing Model

IAES events map to the ISO 13374-2 processing blocks:

| Block | Name | IAES Event |
|-------|------|-----------|
| 1 | Data Acquisition | `asset.measurement` |
| 2 | Data Manipulation | `asset.measurement` (processed values) |
| 3 | State Detection | `asset.health` (anomaly_score) |
| 4 | Health Assessment | `asset.health` (health_index, iso_13374_status) |
| 5 | Prognostic Assessment | `asset.health` (rul_days) |
| 6 | Advisory Generation | `asset.health` (recommended_action) + `maintenance.work_order_intent` |

IAES is an event standard, not a processing pipeline. The 6-block model describes internal processing stages; IAES captures the outputs of those stages as events. See `skills/iso-13374/SKILL.md` for implementation guidance.

## License

IAES is an open specification licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Implementations may be proprietary.

---

*IAES v1.2 — March 2026*
*Created by the [Wertek AI](https://wertek.ai) team.*
*Reference implementation: [Wertek Integration Framework](https://github.com/wertek-ai/wertek-integrations)*
