\# Assignment 2 – UI Impact Analysis (HRM List)



\## 1. Addressed Component

\*\*Module:\*\* Human Resource Management (HRM)  

\*\*File:\*\* `views/\_list.html`  

\*\*Page:\*\* HRM Staff List UI  



This UI is used to display, search and manage staff records.  

It contains the title, Add button, map view and staff table.



The original layout caused usability issues:

\- Add button not clearly visible

\- Map and table not visually separated

\- Poor alignment reduced readability



---



\## 2. Impact Analysis Graph (UI Flow)



```mermaid

graph TD

&nbsp; U\[User] --> B\[Browser]

&nbsp; B --> UI\[HRM List UI (views/\_list.html)]



&nbsp; UI --> NAV\[Navigation Menu]

&nbsp; UI --> ACT\[User Actions: Add / View / Search]

&nbsp; UI --> MAP\[Map Section]

&nbsp; UI --> TBL\[Table/List]



&nbsp; ACT --> ROUTE\[URL Routes]

&nbsp; ROUTE --> CTRL\[Controllers]

&nbsp; CTRL --> MODEL\[Models]

&nbsp; MODEL --> DB\[(Database)]



&nbsp; TBL --> DATA\[Displayed Staff Data]

&nbsp; DATA --> UX\[User Experience]
3. Key Components Identified
Component	Type	Role
HRM List UI	UI	Displays staff data
Add Button	UI Action	Creates new staff
Map Section	UI Block	Shows staff locations
Table/List	UI Block	Displays staff records
Controllers	Backend	Handle user requests
Database	Data Layer	Stores staff data
4. Impact & Insights

Changes to the HRM List UI affect:

How users navigate the system

Which routes and controllers are triggered

How staff data is queried from the database

User understanding and trust

This UI has medium to high ripple effect because it connects the user directly to backend logic and data.

5. Maintenance Type (Appendix Classification)

This UI work is classified as:

Perfective Maintenance
Improves layout, usability and readability

Preventive Maintenance
Reduces user mistakes and future maintenance effort

6. Testing Implications

UI changes require:

Manual UI testing (buttons, layout, map, table)

Validation that navigation and data display still work

7. Summary

The HRM List UI is a critical user-facing component.
Small UI changes can affect navigation, controllers and database access.

This impact analysis shows that UI maintenance must be carefully tested to avoid breaking user workflows.



