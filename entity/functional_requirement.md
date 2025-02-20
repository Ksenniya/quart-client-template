Here are the well-formatted final functional requirements for your Finnish Companies Data Retrieval and Enrichment Application:

### Functional Requirements

#### 1. Data Retrieval
- **FR-1**: The application must allow users to retrieve company information using a company name or a partial name.
  - **Endpoint**: `GET /companies`
  - **Request Parameters**:
    - `name`: string (required)
  - **Response**:
    - Status 200: JSON array of company objects, each containing:
      - `companyName`: string
      - `businessId`: string
      - `companyType`: string
      - `registrationDate`: string (date in `YYYY-MM-DD` format)
      - `status`: string (Active/Inactive)
      - `lei`: string (or "Not Available")

#### 2. Filtering
- **FR-2**: The application must filter out inactive company names after retrieving data from the Finnish Companies Registry API.
  - Criteria for active status: The application considers a company active if its business status is marked as active in the registry.

#### 3. LEI Data Enrichment
- **FR-3**: The application must enrich the retrieved company data by searching for the Legal Entity Identifier (LEI) from official LEI registries or reliable financial data sources.
  - If an LEI is found, it should be included in the response; otherwise, the field should indicate "Not Available".

#### 4. Output Format
- **FR-4**: The application must return the final output in a structured format, either JSON (default) or CSV (optional based on user preference).

#### 5. Error Handling
- **FR-5**: The application must provide appropriate error messages for various scenarios, including:
  - Status 400: Bad Request
  - Status 429: Too Many Requests
  - Status 500: Internal Server Error
  - Status 503: Service Unavailable

#### 6. Optional Features
- **FR-6**: The application may provide advanced search functionalities, allowing users to filter results by additional parameters (e.g., location, business ID, company type).
  - **Endpoint**: `GET /companies/search`
  - **Request Parameters**: Additional optional parameters (e.g., `location`, `businessId`, `companyForm`, etc.)

### User Stories Overview

1. As a user, I want to retrieve company information by name to find details about specific companies.
2. As a user, I want the application to filter out inactive companies so that I only see active companies in the results.
3. As a user, I want to enrich the company data with the Legal Entity Identifier (LEI) to have complete information on the companies.
4. As a user, I want to receive the results in a structured format (JSON or CSV) to utilize the data easily.

These functional requirements provide a solid foundation for your application development. If you need further modifications or additional details, feel free to ask!