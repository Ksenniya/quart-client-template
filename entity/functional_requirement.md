Here’s a well-formatted outline of the final functional requirements for your Finnish Companies Data Retrieval and Enrichment Application:

---

## Functional Requirements

### 1. Data Retrieval
- **User Story:** As a user, I want to retrieve company information by providing a company name so that I can find relevant company details.
- **API Endpoint:** 
  - **GET /companies**
    - **Request Parameters:**
      - `name` (string): The company name to search for. This can be a partial name.
    - **Response Format:**
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

### 2. Filtering
- **User Story:** As a user, I want to filter out inactive companies from the results so that I only see active companies.
- **Functionality:**
  - The application must filter out any companies that are marked as inactive based on the business status from the Finnish Companies Registry.

### 3. LEI Data Enrichment
- **User Story:** As a user, I want the application to enrich the company data with the Legal Entity Identifier (LEI) so that I have complete information about the company.
- **Functionality:**
  - The application must search for the LEI of each active company from official LEI registries or reliable financial data sources.
  - If an LEI is found, it should be included in the output; otherwise, the LEI field should show "Not Available".

### 4. Output Format
- **User Story:** As a user, I want to receive the output in JSON or CSV format so that I can easily use the data in my applications.
- **Response Format Options:**
  - JSON format as described above.
  - CSV format should be structured with the following columns:
    - Company Name
    - Business ID
    - Company Type
    - Registration Date
    - Status (Active/Inactive)
    - LEI (if available)

### 5. Error Handling
- **Functionality:**
  - The application should handle API errors gracefully and return appropriate HTTP status codes (e.g., 400 for bad requests, 500 for server errors).
  - The response should include an error message in JSON format:
    ```json
    {
      "error": {
        "code": "400",
        "message": "Bad request"
      }
    }
    ```

### 6. Performance Requirements
- The application should aim for a response time of less than 2 seconds for API requests.
- The application should handle up to 100 concurrent users without performance degradation.

### 7. Authentication and Authorization
- **Functionality:**
  - The application must implement user authentication to restrict access to authorized users only.
  - Different access levels should be defined (e.g., admin, user) with varying permissions.

---

This finalized outline of functional requirements provides a comprehensive guide for developing the application, ensuring all necessary features and functionalities are clearly defined.