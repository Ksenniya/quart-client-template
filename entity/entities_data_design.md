Based on the provided `prototype_cyoda.py`, we can create the following Mermaid Entity-Relationship (ER) diagrams and class diagrams for the entity model "companies". 

### Mermaid ER Diagram for "companies"

```mermaid
erDiagram
    COMPANY {
        string technical_id PK "Unique identifier for the job"
        string status "Current status of the job (e.g., processing, completed, failed)"
        string requestedAt "Timestamp of when the job was requested"
        string completedAt "Timestamp of when the job was completed"
        string error "Error message if the job failed"
        array results "List of enriched company data"
    }

    COMPANY_RESULT {
        string companyName "Name of the company"
        string businessId "Unique business identifier"
        string companyType "Type of the company"
        string registrationDate "Date of registration"
        string status "Current status of the company"
        string lei "Legal Entity Identifier (LEI)"
    }

    COMPANY ||--o{ COMPANY_RESULT : has
```

### Mermaid Class Diagram for "companies"

```mermaid
classDiagram
    class CompanyQueryRequest {
        +string companyName
        +string outputFormat
    }

    class QueryResponse {
        +string jobId
        +string status
        +string requestedAt
    }

    class Company {
        +string technical_id
        +string status
        +string requestedAt
        +string completedAt
        +string error
        +array results
    }

    class CompanyResult {
        +string companyName
        +string businessId
        +string companyType
        +string registrationDate
        +string status
        +string lei
    }

    CompanyQueryRequest --> QueryResponse : returns
    Company --> CompanyResult : contains
```

### Explanation

1. **ER Diagram**:
   - The `COMPANY` entity represents the job record created when a company query is initiated. It contains fields for tracking the job's status, timestamps, and results.
   - The `COMPANY_RESULT` entity represents the individual company data that is enriched and returned as part of the job results. Each company has attributes like `companyName`, `businessId`, `companyType`, etc.
   - The relationship indicates that a `COMPANY` can have multiple `COMPANY_RESULT` entries.

2. **Class Diagram**:
   - The `CompanyQueryRequest` class represents the request structure for querying companies, containing the company name and output format.
   - The `QueryResponse` class represents the response structure that includes the job ID, status, and requested timestamp.
   - The `Company` class encapsulates the job's metadata and results.
   - The `CompanyResult` class encapsulates the details of each enriched company.
   - The arrows indicate the relationships between the classes, showing that a `CompanyQueryRequest` leads to a `QueryResponse`, and a `Company` contains multiple `CompanyResult` instances.

These diagrams provide a clear representation of the entities and their relationships as defined in the provided code.