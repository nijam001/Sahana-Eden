# WIF3005 Software Maintenance and Evolution

## Assignment 2: Impact Analysis

---

## Overview

For this assignment, each student will work individually on the selected repository of your group project. You are required to perform an impact analysis on the project you have previously selected. The primary objective is to analyze how various components and changes in your project affect each other and the overall system.

---

## Instructions

### 1. Fork the Repository

- Ensure that one of your team members has forked the original legacy system repository.
- Work only in the forked repository, not the original one.

### 2. Create a New Branch

In the forked repository, you are required to create a new branch using this format:

```
assignment2_<your name>
```

### 3. Select the Impact Analysis Graph

Choose **one** of the following graph options to analyze the system:

| Option | Graph Type | Description |
|--------|------------|-------------|
| 1 | **Traceability Graph** | Illustrate the relationships between requirements, design, and implementation |
| 2 | **Software Lifecycle Objects** | Map out the stages of your software's lifecycle and the relationships between them |
| 3 | **Call Graph** | Visualize the functions or methods within your code and how they interact during execution |
| 4 | **Program Dependency Graph** | Show the dependencies between different modules or components of your software |

### 4. Perform the Impact Analysis (Individually)

- Implement the chosen graph by analyzing the components of your legacy system.
- You can draw the graph using any online tools or hand-drawing is also accepted.
- Ensure the graph is:
  - Clear
  - Labeled correctly
  - Shows the relationships and dependencies effectively

> [!TIP]
> Refer to lecture notes **Chapter 6** for guidance on creating impact analysis graphs.

### 5. Create a Pull Request (PR)

- Once the graph is completed, submit your work as a PR (as done in Assignment 1)
- Ensure the PR is comparing your branch with the main branch of the forked repository.
- In the PR, include a description (the 5 marks for the assignment will be based on what is reported here).

---

## PR Description Requirements

The PR description should include:

| Component | Marks | Description |
|-----------|-------|-------------|
| **Addressed Component/Module/Part** | 1 mark | Specify which part of the system you are analyzing |
| **The Graph (Completeness)** | 3 marks | The complete graph you created, properly labeled and clear |
| **Impact/Insights** | 1 mark | The impact or insights gained from the analysis |
| **Total** | **5 marks** | |

---

## Submission Instructions

### 7. Submit Your Pull Request

- Once the PR is created with a complete description, submit it.
- Add **@suhadaudd11** as a reviewer or assignee for the PR, enabling direct feedback and grading.

> [!CAUTION]
> No marks will be given for pull requests that are not assigned by the deadline.

---

## Deadline

> [!IMPORTANT]
> **End of Week 11 - Midnight (12:00 AM) on Sunday, 4 Jan 2026**

---

## Checklist for Assignment 2

- [ ] Created a new branch (`assignment2_<your name>`) in the forked repository
- [ ] Selected impact analysis graph and confirmed it with team members
- [ ] Completed drawing the graph and documented it
- [ ] Created a pull request (PR) with a detailed description, including:
  - [ ] The addressed issue
  - [ ] The complete graph
  - [ ] The impact or insights gained from the analysis
- [ ] Added @suhadaudd11 as a reviewer or assignee on the pull request

---

## Graph Options Summary

### Option 1: Traceability Graph
```
Requirements ──→ Design ──→ Implementation ──→ Testing
```
Shows how requirements flow through the development lifecycle.

### Option 2: Software Lifecycle Objects
```
Planning ──→ Analysis ──→ Design ──→ Development ──→ Testing ──→ Deployment
```
Maps the stages and their interconnections.

### Option 3: Call Graph
```
main() ──→ function_a() ──→ function_b()
                        ──→ function_c()
```
Visualizes function/method invocations and interactions.

### Option 4: Program Dependency Graph
```
Module A ──→ Module B
         ──→ Module C ──→ Module D
```
Shows dependencies between software components.

---

## Summary

| Step | Action | Status |
|------|--------|--------|
| 1 | Fork repository (group action) | ⬜ |
| 2 | Create branch `assignment2_<name>` | ⬜ |
| 3 | Select graph type | ⬜ |
| 4 | Perform impact analysis | ⬜ |
| 5 | Create PR with description | ⬜ |
| 6 | Add @suhadaudd11 as reviewer | ⬜ |
| 7 | Submit before deadline | ⬜ |
