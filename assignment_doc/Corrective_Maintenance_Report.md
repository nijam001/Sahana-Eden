# Corrective Maintenance Report

## Sahana-Eden GIS Module - `ldata()` Function

---

## 1. Overview

This document describes the **Corrective Maintenance** performed on the `ldata()` function in the Sahana-Eden GIS module. The maintenance focused on fixing bugs related to input validation and error handling.

---

## 2. Maintenance Classification

| Classification Scheme | Type | Description |
|----------------------|------|-------------|
| **Intention-based** | Corrective | Fixing defects in error handling |
| **Activity-based** | Corrective | Correcting software defects |
| **Evidence-based** | Defects | Addressing bugs found during analysis |

---

## 3. Problems Identified

During the Impact Analysis (Assignment 2), the following bugs were identified in the `ldata()` function:

### Bug #1: Generic Error Response
- **Location:** Line 700-703
- **Issue:** When `location_id` is missing, HTTP 400 is returned without any message
- **Impact:** Users cannot understand what went wrong

### Bug #2: No Numeric Validation
- **Location:** Line 700-701
- **Issue:** No validation if `location_id` is a valid number
- **Impact:** May cause unexpected errors or crashes

### Bug #3: Invalid Level Parameter
- **Location:** Line 708-709
- **Issue:** If level parameter is not numeric, code crashes with ValueError
- **Impact:** Application crash on invalid input

### Bug #4: Silent Failure for Non-Existent Location
- **Location:** Line 789-795
- **Issue:** Returns empty `{}` instead of proper 404 error
- **Impact:** Users don't know if location exists or not

---

## 4. Solution Implemented

### 4.1 Input Validation

**Before:**
```python
req_args = request.args
try:
    location_id = req_args[0]
except:
    raise HTTP(400)  # No message

if len(req_args) > 1:
    output_level = int(req_args[1])  # May crash
```

**After:**
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

### 4.2 Location Not Found (404)

**Before:**
```python
try:
    id_level = int(locations.as_dict()[_loc_id]["level"][1:])
except:
    return "{}"  # Silent failure
```

**After:**
```python
try:
    id_level = int(locations.as_dict()[_loc_id]["level"][1:])
except:
    # CORRECTIVE MAINTENANCE: Return 404 for non-existent location
    raise HTTP(404, "Location not found: %s" % _loc_id)
```

---

## 5. Visual Diff Summary

```diff
  def ldata():
      req_args = request.args
+     
+     # CORRECTIVE MAINTENANCE: Input Validation & Error Handling
      try:
          location_id = req_args[0]
+         int(location_id)  # Validate numeric
-     except:
-         raise HTTP(400)
+     except IndexError:
+         raise HTTP(400, "Missing required parameter: location_id")
+     except ValueError:
+         raise HTTP(400, "Invalid location_id: must be numeric")

      if len(req_args) > 1:
-         output_level = int(req_args[1])
+         try:
+             output_level = int(req_args[1])
+             if output_level < 0 or output_level > 5:
+                 raise HTTP(400, "Invalid level: must be between 0 and 5")
+         except ValueError:
+             raise HTTP(400, "Invalid level parameter: must be numeric")
```

---

## 6. Test Cases

| Test Case | URL | Expected Result | Status |
|-----------|-----|-----------------|--------|
| Valid request | `/gis/ldata/1` | JSON response | ✅ Works |
| Missing ID | `/gis/ldata/` | HTTP 400: "Missing required parameter" | ✅ Fixed |
| Invalid ID | `/gis/ldata/abc` | HTTP 400: "must be numeric" | ✅ Fixed |
| Invalid level | `/gis/ldata/1/xyz` | HTTP 400: "must be numeric" | ✅ Fixed |
| Non-existent | `/gis/ldata/99999` | HTTP 404: "Location not found" | ✅ Fixed |

---

## 7. Impact Assessment

| Aspect | Assessment |
|--------|------------|
| **Risk Level** | Low - Input validation only |
| **Breaking Changes** | Minor - Empty `{}` now returns 404 |
| **Backward Compatibility** | High - Valid requests unchanged |
| **Lines Changed** | ~30 lines added |

---

## 8. Summary

| Metric | Value |
|--------|-------|
| **Bugs Fixed** | 4 |
| **Maintenance Type** | Corrective |
| **Files Modified** | 1 (`controllers/gis.py`) |
| **Test Coverage** | 5 test cases |

---

## References

- **File:** `controllers/gis.py`
- **Lines:** 698-730
- **Branch:** `maintenance_alnijam`
- **Date:** January 5, 2026
