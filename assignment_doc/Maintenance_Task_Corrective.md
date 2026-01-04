# Maintenance Task Documentation

## Corrective Maintenance: Fix Bugs in `ldata()` Function

---

## Maintenance Classification

### 1. Intention-based Classification
| Type | Applies? | Description |
|------|----------|-------------|
| **Corrective** | ✅ | **Fixing bugs and error handling issues** |
| Adaptive | ❌ | Not adapting to new environment |
| Perfective | ❌ | Not improving performance |
| Preventive | ❌ | Not preventing future issues |

### 2. Activity-based Classification
| Type | Applies? | Description |
|------|----------|-------------|
| **Corrective** | ✅ | **Correcting defects in error handling** |
| Enhancive | ❌ | Not enhancing functionality |

### 3. Evidence-based Classification

**Category: Defects**
| Type | Applies? | Description |
|------|----------|-------------|
| **Defects** | ✅ | **Fixing bugs in input validation and error responses** |
| User Request | ❌ | Not user-requested |
| Performance | ❌ | Not performance related |

---

## Addressed Component

| Attribute | Value |
|-----------|-------|
| **Module** | GIS (Geographic Information System) |
| **Function** | `ldata()` |
| **File** | `controllers/gis.py` |
| **Branch** | `maintenance_alnijam` |

---

## Problems Fixed

### Bug 1: Missing Parameter Error Message
**Before:** Generic HTTP 400 with no message  
**After:** HTTP 400 with "Missing required parameter: location_id"

### Bug 2: Invalid Location ID (Non-numeric)
**Before:** Crashes or returns empty JSON  
**After:** HTTP 400 with "Invalid location_id: must be numeric"

### Bug 3: Invalid Level Parameter
**Before:** May crash with ValueError  
**After:** HTTP 400 with "Invalid level parameter: must be numeric"

### Bug 4: Non-Existent Location
**Before:** Returns empty `{}`  
**After:** HTTP 404 with "Location not found: [id]"

---

## Code Changes

### Before (Original)
```python
req_args = request.args
try:
    location_id = req_args[0]
except:
    raise HTTP(400)  # No error message

if len(req_args) > 1:
    output_level = int(req_args[1])  # May crash if not numeric
```

### After (With Bug Fixes)
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
```

---

## Test Cases

| Test | URL | Expected Result |
|------|-----|-----------------|
| Missing ID | `/gis/ldata/` | HTTP 400: "Missing required parameter: location_id" |
| Invalid ID | `/gis/ldata/abc` | HTTP 400: "Invalid location_id: must be numeric" |
| Invalid Level | `/gis/ldata/1/abc` | HTTP 400: "Invalid level parameter: must be numeric" |
| Non-existent | `/gis/ldata/99999` | HTTP 404: "Location not found: 99999" |
| Valid Request | `/gis/ldata/1` | JSON response (same as before) |

---

## Summary

| Aspect | Result |
|--------|--------|
| **Maintenance Type** | Corrective |
| **Bugs Fixed** | 4 |
| **Breaking Changes** | Yes - empty `{}` now returns 404 |
| **Test Status** | Ready for testing |

---

**Date:** January 5, 2026  
**Author:** Al Nijam  
**Branch:** `maintenance_alnijam`
