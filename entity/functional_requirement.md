# Functional Requirements for the Finnish Companies Data Retrieval and Enrichment Application

## 1. Overview
The application will retrieve and enrich data from the Finnish Companies Registry based on user-provided company names. It will filter out inactive companies and enrich the data with Legal Entity Identifiers (LEIs) from reliable sources.

## 2. Functional Requirements

### 2.1 Data Retrieval
- **Endpoint**: `POST /api/companies/query`
- **Description**: Accepts a company name and optional parameters to query the Finnish Companies Registry API.
- **Input**:
  - `companyName` (string, required): The name or partial name of the company to search.
  - `searchParameters` (object, optional):
    - `location` (string): Town or city.
    - `businessId` (string): Business ID.
    - `companyForm` (string): Form of the company (e.g., OY).
    - `registrationDateStart` (string, format: yyyy-mm-dd): Start date for registration.
    - `registrationDateEnd` (string, format: yyyy-mm-dd): End date for registration.
- **Output**:
  - `queryId` (string): A unique identifier for the query.
  - `status` (string): Indicates processing status (e.g., "processing", "completed").
  - `message` (string): Information about the status of the request.

### 2.2 Filtering
- The application must filter the retrieved data to exclude any companies marked as inactive in the Finnish Companies Registry.
- Only active names should be retained in the output.

### 2.3 LEI Data Enrichment
- The application must perform a web search to fetch the LEI for each active company.
- LEIs must be retrieved from official registries or reliable financial data sources.
- If no LEI is found, the field should be marked as "Not Available".

### 2.4 Output Format
- **Endpoint**: `GET /api/companies/results/{queryId}`
- **Description**: Retrieves the processed results using the unique query ID.
- **Output**:
  - `queryId` (string): The unique query identifier.
  - `results` (array): List of enriched company data objects containing:
    - `companyName` (string)
    - `businessId` (string)
    - `companyType` (string)
    - `registrationDate` (string)
    - `status` (string, "Active" or "Inactive")
    - `lei` (string or "Not Available")
  - `retrievedAt` (string, format: ISO 8601): Timestamp of when the results were retrieved.

### 2.5 Error Handling
- The application must handle errors gracefully and return appropriate HTTP status codes and messages based on:
  - Bad requests (e.g., invalid parameters).
  - No active companies found.
  - External service failures (e.g., API unavailability).

## 3. User Interaction Flow
1. User submits a company name via the `POST /api/companies/query` endpoint.
2. The system processes the request, retrieves data from the Finnish Companies Registry, filters inactive companies, and enriches data with LEI.
3. The system returns a unique `queryId` and a processing status.
4. User retrieves results using `GET /api/companies/results/{queryId}`.
5. The system returns the enriched company data or an appropriate error message. 

These functional requirements ensure that the application meets the essential business logic and user needs for retrieving and enriching company data from the Finnish Companies Registry.