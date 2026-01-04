# Maintenance Tasks Overview

## Group Project: Sahana-Eden GIS Module

This document outlines potential maintenance tasks for the `ldata()` function and GIS module.

---

## ✅ Completed Tasks

### 1. Perfective Maintenance (Caching)
**Status:** Done  
**Branch:** `maintenance_alnijam`

Added `cache.ram` caching to reduce response time from 15ms to 0ms.

### 2. Corrective Maintenance (Bug Fixes)
**Status:** Done  
**Branch:** `maintenance_alnijam`

Fixed input validation, HTTP 400/404 error responses for invalid inputs.

---

## Available Maintenance Tasks

### 1. Corrective Maintenance

**Goal:** Fix bugs and edge cases

| Task | Description | Complexity |
|------|-------------|------------|
| Handle invalid location IDs | Return proper 404 instead of empty `{}` | Low |
| Fix race condition in cache | Add thread-safe cache access | Medium |
| Handle database connection errors | Graceful error handling | Medium |
| Fix missing level edge cases | Improve handling of gaps in hierarchy | High |

**Example Change:**
```python
# Before: Returns empty {} for invalid ID
return "{}"

# After: Return proper HTTP 404
raise HTTP(404, "Location not found")
```

---

### 2. Preventive Maintenance

**Goal:** Prevent future issues, improve maintainability

| Task | Description | Complexity |
|------|-------------|------------|
| Add comprehensive logging | Log all requests and errors | Low |
| Add input validation | Validate location_id format | Low |
| Add type hints | Document parameter types | Low |
| Add docstring improvements | Better function documentation | Low |
| Add deprecation warnings | Prepare for future API changes | Medium |

**Example Change:**
```python
# Add type hints
def ldata() -> str:
    """
    Return JSON of location hierarchy.
    
    Args:
        request.args[0]: Location ID (int)
        request.args[1]: Optional output level (int)
    
    Returns:
        JSON string with location data
        
    Raises:
        HTTP(400): If location_id is missing
        HTTP(404): If location not found
    """
```

---

### 3. Adaptive Maintenance

**Goal:** Adapt to new requirements or environment

| Task | Description | Complexity |
|------|-------------|------------|
| Add API versioning | Support `/v1/gis/ldata/` and `/v2/gis/ldata/` | Medium |
| Add pagination support | Return paginated results for large datasets | Medium |
| Add filter parameters | Filter by level, name pattern, etc. | Medium |
| Add GeoJSON output format | Support `?format=geojson` parameter | High |
| Support WebSocket updates | Real-time location updates | High |

**Example Change:**
```python
# Add pagination support
# GET /gis/ldata/1?page=1&limit=50
page = request.vars.get("page", 1)
limit = request.vars.get("limit", 100)
```

---

### 4. Groomative Maintenance

**Goal:** Restructure code for better maintainability

| Task | Description | Complexity |
|------|-------------|------------|
| DRY with `_locations()` | Extract shared logic to service layer | High |
| Create LocationService class | Centralize location data access | High |
| Separate concerns | Split into query, process, format layers | Medium |
| Add unit tests | Increase test coverage | Medium |
| Extract constants | Move magic numbers to config | Low |

**Example Change:**
```python
# Before: Duplicated code in ldata() and LocationSelector._locations()

# After: Shared service
class LocationDataService:
    @staticmethod
    def get_location_hierarchy(location_id, level=None, language="en"):
        # Shared implementation
        pass

# In ldata():
return LocationDataService.get_location_hierarchy(location_id, level, language)

# In LocationSelector:
LocationDataService.get_location_hierarchy(...)
```

---

## Recommended Priority

| Priority | Task | Type | Reason |
|----------|------|------|--------|
| 1 | ✅ Add caching | Perfective | Done - Major performance gain |
| 2 | Add input validation | Preventive | Easy, improves robustness |
| 3 | Add comprehensive logging | Preventive | Easy, helps debugging |
| 4 | Handle invalid location IDs | Corrective | Improves user experience |
| 5 | Extract to LocationService | Groomative | Reduces technical debt |

---

## Classification Summary

| Type | Intention-based | Activity-based | Evidence-based |
|------|-----------------|----------------|----------------|
| Caching | Perfective | Enhancive | Performance |
| Bug fixes | Corrective | Corrective | Defects |
| Logging | Preventive | Preventive | Reliability |
| Refactoring | - | Reductive | Maintainability |
| New features | Adaptive | Enhancive | User Request |

---

**Note:** Each task should be implemented on a separate branch and documented with before/after comparison.
