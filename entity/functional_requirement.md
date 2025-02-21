Here are the final functional requirements for your Finnish Companies Data Retrieval and Enrichment Application, formatted for clarity and ease of understanding:

### Functional Requirements

#### 1. User Stories
1. **Search Companies**
   - **As a user**, I want to search for companies by name so that I can retrieve relevant company information.
     - **Acceptance Criteria**:
       - Input: Company name (or partial name).
       - Output: A list of matching companies in JSON format.

2. **Filter Inactive Companies**
   - **As a user**, I want to filter out inactive companies so that I only see active companies in the results.
     - **Acceptance Criteria**:
       - Only active companies are included in the output.

3. **Enrich Company Data with LEI**
   - **As a user**, I want to enrich company data with Legal Entity Identifiers (LEI) so that I have comprehensive information for each company.
     - **Acceptance Criteria**:
       - If available, the LEI should be included in the output.

4. **Output Format Selection**
   - **As a user**, I want the output in either JSON or CSV format so that I can use the data as needed.
     - **Acceptance Criteria**:
       - The output format is selectable.

#### 2. API Endpoints

1. **GET /companies**
   - **Description**: Retrieve company information based on name, location, business ID, or company form.
   - **Request Format**:
     ```http
     GET /companies?name={company_name}&location={location}&businessId={business_id}&companyForm={company_form}
     ```
   - **Response Format** (JSON):
     ```json
     {
       "companies": [
         {
           "companyName": "Example Company",
           "businessId": "1234567-8",
           "companyType": "OY",
           "registrationDate": "2020-01-01",
           "status": "Active",
           "lei": "LEI123456789"
         }
       ]
     }
     ```

2. **GET /companies/lei**
   - **Description**: Enrich company data by retrieving LEI.
   - **Request Format**:
     ```http
     GET /companies/lei?businessId={business_id}
     ```
   - **Response Format** (JSON):
     ```json
     {
       "lei": "LEI123456789"
     }
     ```

### 3. Error Handling
- The application should gracefully handle errors from the API, returning standardized error responses.
- Possible error responses include:
  - **400 Bad Request**: Invalid parameters.
  - **404 Not Found**: No companies found.
  - **500 Internal Server Error**: An unexpected error occurred.

### 4. Output Specifications
- The application must output data in either JSON or CSV format, as specified by the user.
- If no LEI is found for a company, the LEI field should be marked as “Not Available”.

This structured set of functional requirements should serve as a clear guideline for your development process. If there are any specific areas you would like to delve into further, please let me know!