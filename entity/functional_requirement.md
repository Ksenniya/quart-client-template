Here are the well-formatted final functional requirements for your Finnish Companies Data Retrieval and Enrichment Application:

---

### Functional Requirements for Finnish Companies Data Retrieval and Enrichment Application

#### 1. Data Retrieval
- **User Story**: As a user, I want to retrieve company information from the Finnish Companies Registry by providing a company name, so that I can find relevant business details.
- **Requirement**:
  - The application must provide an endpoint to query the Finnish Companies Registry API using a company name or partial name.
- **API Endpoint**: 
  - **GET /companies**
    - **Request**:
      - Query Parameter: `name` (string, required)
    - **Response**:
      - 200 OK: JSON array of matching companies with relevant details.
      - 400 Bad Request: Error message in JSON format (e.g., malformed request).
      - 429 Too Many Requests: Rate limit message in plain text.
      - 500 Internal Server Error: Error message in JSON format.

#### 2. Filtering
- **User Story**: As a user, I want the application to filter out inactive companies, so that I only see active entities.
- **Requirement**:
  - The application must filter the retrieved company data to exclude any companies marked as inactive based on the business status provided by the registry.

#### 3. LEI Data Enrichment
- **User Story**: As a user, I want the application to enrich company data by fetching the Legal Entity Identifier (LEI), so that I can have complete and verified information about the company.
- **Requirement**:
  - The application must provide an endpoint to fetch the LEI for each active company from reliable financial data sources.
- **API Endpoint**:
  - **GET /companies/{id}/lei**
    - **Request**:
      - Path Parameter: `id` (string, required)
    - **Response**:
      - 200 OK: JSON containing LEI or "Not Available" if no LEI is found.
      - 404 Not Found: Error message in JSON format if the company does not exist.

#### 4. Output Format
- **User Story**: As a user, I want the output to be in JSON or CSV format, so that I can easily consume or manipulate the data.
- **Requirement**:
  - The application must return the final output in a structured format based on user preference:
    - Fields included in the output:
      - Company Name
      - Business ID
      - Company Type
      - Registration Date
      - Status (Active/Inactive)
      - LEI (if available; otherwise marked as "Not Available").

---

This format clearly outlines the functional requirements, user stories, and API endpoints needed for your application. If you need any additional information or adjustments, feel free to ask!