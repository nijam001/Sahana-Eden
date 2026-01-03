# Impact Analysis – Organisation Controller (Call Graph)

## 1. Addressed Component / Module

This impact analysis focuses on the **Organisation Registry** module of the
Sahana-Eden legacy system.

The specific component analysed is the `organisation()` RESTful CRUD controller
function located in:

- `controllers/org.py`

The `organisation()` function is the primary entry point for managing
organisation records in the system. It handles user requests related to
creating, viewing, updating, and deleting organisation data.

---

## 2. Impact Analysis Graph Type

**Graph Type:** Call Graph  
**Analysis Method:** Dependency-based Impact Analysis (Chapter 6)

According to Chapter 6 of the lecture notes, a Call Graph is a directed graph
where:

- Nodes represent functions or system components
- Directed edges represent invocation (calling) relationships
- A change in a function may impact all nodes reachable from it in the graph

---

## 3. Call Graph Representation

### 3.1 Call Graph Diagram

```mermaid
graph TD
    A[organisation() Controller<br/>controllers/org.py]
    B[s3db.org_organisation_controller()<br/>Model Layer]
    C[S3CRUD Framework]
    D[org_organisation<br/>Database Table]

    A -->|invokes| B
    B -->|uses| C
    C -->|accesses| D

