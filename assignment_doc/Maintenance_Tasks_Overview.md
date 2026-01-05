# Maintenance Tasks Overview

## Group Project: Sahana-Eden GIS Module

This document provides a comprehensive overview of all maintenance tasks performed on the GIS module. Each task is documented with its classification, implementation details, and results.

---

## ✅ Completed Maintenance Tasks

---

### 1. Perfective Maintenance: Performance Optimization via Caching

| Attribute | Value |
|-----------|-------|
| **Status** | ✅ Completed |
| **Branch** | `maintenance_alnijam` |
| **File Modified** | `controllers/gis.py` |
| **Lines Affected** | 667-827 |
| **Documentation** | [Maintenance_Task_Perfective.md](./Maintenance_Task_Perfective.md) |

#### Problem Identified

The `ldata()` function queries the database on **every single request** to fetch location hierarchy data. This is highly inefficient because:

1. **Location hierarchies are static data** — they change infrequently (countries, states, cities rarely change)
2. **High repetition** — the same locations are requested repeatedly by multiple users navigating the same forms
3. **Database latency** — each query adds 10-20ms of latency to the response time
4. **Resource waste** — high traffic causes unnecessary load on the database server, potentially affecting other operations

#### Solution Implemented

Added an **in-memory cache with Time-To-Live (TTL)** using web2py's built-in `cache.ram` mechanism:

```python
# Cache configuration
CACHE_TTL = 60  # 1 minute cache expiry

# Generate unique cache key based on request parameters
cache_key = "ldata_%s_%s_%s" % (location_id, output_level, language)

# Use web2py cache.ram for in-memory caching
result = cache.ram(cache_key, fetch_location_data, time_expire=CACHE_TTL)
```

**Key Design Decisions:**
- **Cache key structure**: Includes `location_id`, `output_level`, and `language` to ensure different requests get different cached responses
- **TTL of 60 seconds**: Balances between performance gains and data freshness
- **In-memory storage**: Uses web2py's `cache.ram` for fastest possible retrieval

#### Performance Results

| Metric | Before (No Cache) | After (With Cache) | Improvement |
|--------|-------------------|-------------------|-------------|
| Response Time | 15.44 ms | 0.00 ms | **99.99%** |
| Database Queries | 1 per request | 0 (cached) | **-100%** |
| Server Load | Linear with traffic | Constant | **Significant** |

#### Maintenance Classification

| Scheme | Classification | Justification |
|--------|----------------|---------------|
| **Intention-based** | Perfective | Improving performance without changing external behavior |
| **Activity-based** | Enhancive | Enhancing system performance characteristics |
| **Evidence-based** | Performance | Addressing response time and efficiency concerns |

---

### 2. Corrective Maintenance: Input Validation and Error Handling (ldata)

| Attribute | Value |
|-----------|-------|
| **Status** | ✅ Completed |
| **Branch** | `maintenance_alnijam` |
| **File Modified** | `controllers/gis.py` |
| **Lines Affected** | 667-750 |
| **Documentation** | [Maintenance_Task_Corrective.md](./Maintenance_Task_Corrective.md) |

#### Problems Identified

The original `ldata()` function had several bugs related to input validation and error handling:

| Bug # | Problem | Original Behavior | Impact |
|-------|---------|-------------------|--------|
| 1 | Missing location_id parameter | Generic HTTP 400 with no message | Developers cannot diagnose issues |
| 2 | Non-numeric location_id (e.g., `/gis/ldata/abc`) | Application crash or empty JSON | Security risk, poor UX |
| 3 | Invalid level parameter (e.g., `/gis/ldata/1/xyz`) | ValueError exception crash | Application instability |
| 4 | Non-existent location (e.g., `/gis/ldata/99999`) | Returns empty `{}` | Misleading response, hard to debug |

#### Solution Implemented

Added comprehensive input validation with descriptive error messages:

```python
# CORRECTIVE MAINTENANCE: Input Validation & Error Handling
req_args = request.args

# Validate location_id is provided and is numeric
try:
    location_id = req_args[0]
    int(location_id)  # Validate numeric
except IndexError:
    raise HTTP(400, "Missing required parameter: location_id")
except ValueError:
    raise HTTP(400, "Invalid location_id: must be numeric")

# Validate output_level if provided
if len(req_args) > 1:
    try:
        output_level = int(req_args[1])
        if output_level < 0 or output_level > 5:
            raise HTTP(400, "Invalid level: must be between 0 and 5")
    except ValueError:
        raise HTTP(400, "Invalid level parameter: must be numeric")

# Check if location exists in database
if not location_data:
    raise HTTP(404, "Location not found: %s" % location_id)
```

#### Maintenance Classification

| Scheme | Classification | Justification |
|--------|----------------|---------------|
| **Intention-based** | Corrective | Fixing bugs in input validation and error handling |
| **Activity-based** | Corrective | Correcting defects in the codebase |
| **Evidence-based** | Defects | Addressing identified software defects |

---

### 3. Preventive Maintenance: Documentation and Logging

| Attribute | Value |
|-----------|-------|
| **Status** | ✅ Completed |
| **Branch** | `maintenance_alnijam` |
| **File Modified** | `controllers/gis.py` |
| **Lines Affected** | 667-720 |
| **Documentation** | [Maintenance_Task_Preventive.md](./Maintenance_Task_Preventive.md) |

#### Problems Identified

The original code lacked proper documentation and logging, which leads to:

1. **Difficult debugging** — when issues occur in production, there's no way to trace what happened
2. **Poor maintainability** — new developers struggle to understand the function's purpose and behavior
3. **Missing API contract** — no clear documentation of expected inputs, outputs, and error conditions
4. **No maintenance history** — changes made to the function are not tracked in the code itself

#### Solution Implemented

- Added comprehensive docstring with Args, Returns, Raises, and URL patterns
- Added structured logging with `logging.getLogger("eden.gis.ldata")`
- Documented all maintenance changes in the docstring

#### Maintenance Classification

| Scheme | Classification | Justification |
|--------|----------------|---------------|
| **Intention-based** | Preventive | Preventing future maintenance issues |
| **Activity-based** | Preventive | Improving code maintainability |
| **Evidence-based** | Reliability | Improving system reliability and debuggability |

---

### 4. Corrective Maintenance: LocationSelector Static Method Bug

| Attribute | Value |
|-----------|-------|
| **Status** | ✅ Completed |
| **Branch** | `maintenance_alnijam` |
| **File Modified** | `modules/core/ui/selectors.py` |
| **Line Changed** | 859 |
| **Documentation** | [Maintenance_Task_Corrective_Selectors.md](./Maintenance_Task_Corrective_Selectors.md) |

#### Problem Identified

The `_locations()` method in `LocationSelector` was decorated with `@staticmethod`, but was incorrectly calling `self._get_location_fields(...)`. This caused a critical `NameError` crash when loading any form with location fields.

**Error:**
```
NameError: name 'self' is not defined
```

#### Root Cause

```python
@staticmethod
def _locations(levels, values, ...):  # No 'self' parameter!
    ...
    fields, left = self._get_location_fields(...)  # BUG: 'self' not defined
```

#### Solution Implemented

Changed from `self` to class name since both methods are static:

```python
# Before (Buggy)
fields, left = self._get_location_fields(gtable, translate, language)

# After (Fixed)
fields, left = LocationSelector._get_location_fields(gtable, translate, language)
```

#### Impact

- **Severity:** Critical (application crash)
- **Affected Pages:** All forms with location fields (Organization, Person, Facility, etc.)

#### Maintenance Classification

| Scheme | Classification | Justification |
|--------|----------------|---------------|
| **Intention-based** | Corrective | Fixing a runtime error (NameError) |
| **Activity-based** | Corrective | Correcting a software defect |
| **Evidence-based** | Defects | Addressing a crash-causing bug |

---

## Summary Table

| # | Maintenance Type | File | Key Change | Status |
|---|-----------------|------|------------|--------|
| 1 | **Perfective** | `gis.py` | Added caching (15ms → 0ms) | ✅ Done |
| 2 | **Corrective** | `gis.py` | Input validation (4 bugs) | ✅ Done |
| 3 | **Preventive** | `gis.py` | Documentation + Logging | ✅ Done |
| 4 | **Corrective** | `selectors.py` | Static method bug fix | ✅ Done |

---

## Classification Summary

| Task | Intention-based | Activity-based | Evidence-based |
|------|-----------------|----------------|----------------|
| Caching | Perfective | Enhancive | Performance |
| Bug Fixes (ldata) | Corrective | Corrective | Defects |
| Documentation | Preventive | Preventive | Reliability |
| Static Method Fix | Corrective | Corrective | Defects |

---

## Code Location Reference

| File | Function/Class | Line Range |
|------|----------------|------------|
| `controllers/gis.py` | `ldata()` | 667-864 |
| `modules/core/ui/selectors.py` | `LocationSelector._locations()` | 711-967 |

---

## References

- **Module:** GIS (Geographic Information System)
- **Branch:** `maintenance_alnijam`
- **Impact Analysis:** [`impact_analysis_gis.md`](../assignment2/impact_analysis_gis.md)

---

**Last Updated:** January 6, 2026  
**Author:** Al Nijam
