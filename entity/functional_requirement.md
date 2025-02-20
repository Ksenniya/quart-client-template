Below is the final, well-formatted set of functional requirements for your Finnish Companies Data Retrieval and Enrichment Application.

─────────────────────────────  
1. Overview  
─────────────────────────────  
The application retrieves company data from the Finnish Companies Registry (using the PRH avoindata API) based on company name searches, filters out any inactive companies, and enriches the active results by fetching the Legal Entity Identifier (LEI) from reliable data sources. The output is provided in a structured format (JSON or CSV).

─────────────────────────────  
2. User Stories  
─────────────────────────────  
• As a user, I want to search for companies using a full or partial company name so that I can quickly retrieve relevant data.  
• As a user, I want the application to return only active companies, ensuring that outdated or inactive entries are not displayed.  
• As a user, I want the system to enrich retrieved active company data with its LEI so that I have complete and authoritative company information.  
• As a user, I want to receive the final data in JSON or CSV format, including standardized fields like Company Name, Business ID, Company Type, Registration Date, Status, and LEI.

─────────────────────────────  
3. Functional Requirements  
─────────────────────────────  

3.1 Data Retrieval  
  - The application must accept a company name (or partial name) as input.  
  - It should query the Finnish Companies Registry API (https://avoindata.prh.fi/opendata-ytj-api/v3/companies) using the provided parameters.  
  - The search must support additional query parameters (e.g., location, businessId, companyForm, etc.) as defined in the source API.  

3.2 Filtering  
  - After data retrieval, the application must filter out companies marked as inactive.  
  - If an entity has multiple names, only the active names should be retained in the results.  
  - An audit log or report can be generated to document any companies filtered out (this is optional).

3.3 LEI Data Enrichment  
  - For every active company, the application must attempt to fetch the corresponding LEI from official LEI registries or other reliable financial data sources.  
  - If an LEI is found, it must be attached to the company record; if not, the LEI field should display “Not Available.”

3.4 Output Formatting  
  - The final structured response must contain the following fields:  
      • Company Name  
      • Business ID  
      • Company Type  
      • Registration Date  
      • Status (Active/Inactive)  
      • LEI (or “Not Available”)  
  - The export format should be either JSON or CSV, based on user preference.

─────────────────────────────  
4. API Endpoints  
─────────────────────────────  

Endpoint 1: GET /companies  
  • Description: Retrieve a list of companies matching the search criteria.  
  • Request Query Parameters:  
      - name (string)  
      - location (string)  
      - businessId (string)  
      - companyForm (string)  
      - mainBusinessLine (string)  
      - registrationDateStart (date, format: yyyy-mm-dd)  
      - registrationDateEnd (date, format: yyyy-mm-dd)  
      - postCode (string)  
      - businessIdRegistrationStart (date, format: yyyy-mm-dd)  
      - businessIdRegistrationEnd (date, format: yyyy-mm-dd)  
      - page (integer)  
  • Response Example (HTTP 200, JSON):  

    [
      {
        "companyName": "Example Company",
        "businessId": "1234567-8",
        "companyType": "OY",
        "registrationDate": "2020-01-01",
        "status": "Active",
        "lei": "LEI1234567890"
      },
      ...
    ]  

Endpoint 2: GET /companies/{id}/lei  
  • Description: Retrieve the LEI information for the company by its Business ID.  
  • Request Parameters:  
      - id (string; Business ID)  
  • Response Example (HTTP 200, JSON):  

    {
      "lei": "LEI1234567890"
    }

  • Response Example for not found (HTTP 404, JSON):  

    {
      "error": "LEI not found"
    }

─────────────────────────────  
5. User-App Interaction Diagram  
─────────────────────────────  

Below is a Mermaid sequence diagram illustrating the typical interaction flow:

--------------------------------------------------------
sequenceDiagram
    participant User
    participant App
    participant API

    User->>App: Enter company name and search criteria
    App->>API: GET /companies?name={companyName}&...
    API-->>App: Return list of companies
    App->>App: Filter out inactive companies
    App->>API: For each active company, GET /companies/{id}/lei
    API-->>App: Return LEI or "Not Available"
    App->>User: Display enriched company data (JSON/CSV)
--------------------------------------------------------

─────────────────────────────  
6. Additional Considerations  
─────────────────────────────  
• Error handling should be incorporated to manage situations where external APIs fail or return errors (e.g., HTTP 429, 500).  
• Consider implementing caching for repeated requests to improve performance.  
• The application could optionally support logging for monitoring filtered results and API call statistics.  
• Future development may involve adding user authentication and additional data enrichment rules if needed.

This concludes the final set of functional requirements. Let me know if further adjustments are needed!