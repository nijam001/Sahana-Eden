\# Impact Analysis – Testing Module (Assignment 2)



\## 1. Selected Component

Testing Module (Automated Testing and Validation Framework)



This component is responsible for verifying the correctness and reliability of the Sahana Eden system through automated testing. It ensures that core functionalities behave as expected and that future changes do not introduce regressions.



---



\## 2. Maintenance Task (Context)

The legacy testing environment in Sahana Eden was found to be unstable due to missing dependencies, broken Robot Framework libraries, and misconfigured environment variables. As a result, automated tests could not be executed reliably.



Although Assignment 2 focuses on impact analysis rather than performing the maintenance itself, this analysis evaluates the impact of stabilizing the testing environment and introducing a minimal, reliable test baseline.



---



\## 3. Technical Impact



Before maintenance:

\- The existing Robot Framework test suite could not run due to missing libraries such as SeleniumLibrary and Gluon.

\- Environment variables (e.g., BASEURL, SERVER, PORT) were not configured, causing test execution failures.

\- The testing pipeline was effectively broken, preventing automated verification of the system.



After maintenance (expected impact):

\- A lightweight Python-based unit testing framework (e.g., unittest or pytest) provides a stable baseline for automated testing.

\- Core validation logic (such as email format checking and password rules) can be tested independently of the full web2py environment.

\- Developers can verify whether changes break important business logic, reducing the risk of introducing defects.



Overall, this significantly improves the maintainability and testability of the system.



---



\## 4. User Impact



End users indirectly benefit from a more reliable testing system:

\- Fewer bugs are released into the production system.

\- Critical disaster management functions are less likely to fail unexpectedly.

\- The system becomes more stable and trustworthy for humanitarian operations.



Although users do not interact with the testing system directly, its stability improves the overall quality of the application they use.



---



\## 5. Developer Impact



For developers, the impact is significant:

\- Changes can be validated automatically instead of relying on manual testing.

\- Developers can refactor or enhance code with more confidence.

\- Debugging time is reduced because errors are detected earlier in the development cycle.



This encourages safer refactoring and supports continuous improvement of the codebase.



---



\## 6. Risks



Potential risks include:

\- The minimal test suite may not fully cover all system functionalities.

\- Full Robot Framework integration still requires additional environment configuration.

\- Developers may rely too heavily on limited unit tests and miss integration issues.



---



\## 7. Mitigation



These risks can be mitigated by:

\- Gradually expanding test coverage as the system evolves.

\- Restoring full Robot Framework support once dependencies and configurations are stabilized.

\- Combining unit tests with manual and integration testing for critical workflows.



---



\## 8. Conclusion



Stabilizing the testing module has a strong positive impact on system reliability, developer productivity, and long-term maintainability. Even a minimal automated test baseline significantly improves the quality of software maintenance for Sahana Eden.



