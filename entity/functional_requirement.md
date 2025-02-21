Here are the well-formatted final functional requirements for your Finnish Companies Data Retrieval and Enrichment Application:

---

### Functional Requirements

#### 1. Overview
The Finnish Companies Data Retrieval and Enrichment Application will retrieve and enrich data from the Finnish Companies Registry and provide users with structured company information.

#### 2. API Endpoints

##### 2.1 POST /companies/search
- **Purpose**: Initiates the data retrieval and enrichment process.
- **Request Format**: 
    ```json
    {
        "companyName": "Example Oy",
        "filters": {
            "registrationDateStart": "2020-01-01",
            "registrationDateEnd": "2020-12-31"
        }
    }
    ```
- **Response Format**: 
    ```json
    {
        "searchId": "unique-search-id",
        "status": "processing"
    }
    ```
- **Notes**:
  - All external calls (to the Finnish Companies Registry API and the LEI data source) and business logic occur here.
  - May involve asynchronous processing.

##### 2.2 GET /companies/results/{searchId}
- **Purpose**: Retrieves the results of the data processing initiated by the POST request.
- **Request**: 
  - Path Parameter: `searchId` (returned from the POST request).
- **Response Format**: 
    ```json
    {
        "searchId": "unique-search-id",
        "results": [
            {
                "companyName": "Example Oy",
                "businessId": "1234567-8",
                "type": "OY",
                "registrationDate": "2010-05-20",
                "status": "Active",
                "LEI": "5493001KJTIIGC8Y1R12"  // or "Not Available"
            }
        ],
        "status": "completed"
    }
    ```
- **Notes**:
  - Used solely to retrieve final results after processing.
  - Response includes the status of the processing.

#### 3. Business Logic
- The application must:
  - Query the Finnish Companies Registry API to retrieve company data based on the provided company name.
  - Filter out inactive companies based on their business status.
  - Enrich each active company with its Legal Entity Identifier (LEI) from reliable sources.
  
#### 4. Output Format
- The final output must be structured in JSON format containing the following fields:
  - `companyName`: Name of the company.
  - `businessId`: Unique identifier for the company.
  - `type`: Type of the company (e.g., OY, OYJ).
  - `registrationDate`: Date of registration.
  - `status`: Active or Inactive status.
  - `LEI`: Legal Entity Identifier or "Not Available".

#### 5. Error Handling
- Implement appropriate error handling for:
  - Invalid input parameters.
  - API request failures (e.g., timeouts, 404 errors).
  - Handling cases where no active companies are found.

---

These functional requirements provide a comprehensive overview of the system's behavior, the API structure, and the expected output format. They serve as a foundational guideline for further development and implementation.