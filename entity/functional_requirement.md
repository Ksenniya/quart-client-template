Below is a final, well-formatted set of functional requirements for the Finnish Companies Data Retrieval and Enrichment Application.

─────────────────────────────  
Functional Requirements Document  
─────────────────────────────

1. Overview  
   The application will allow users to search and retrieve information on Finnish companies from the PRH Avoindata API. It will filter out inactive companies and enrich the data with the Legal Entity Identifier (LEI) when available.

─────────────────────────────  
2. User Stories

2.1 Search and Data Retrieval  
   • As a user, I want to search for companies by name (or partial name) so that I can retrieve relevant company information.  
   • As a user, I want to optionally refine the search using parameters such as location, business ID, or company form.  
   • As a user, I expect the application to return the exact or closest matching companies.

2.2 Filtering  
   • As a user, I want to see only active companies, so the application must filter out any company entries where the business status is not active.  
   • If multiple names exist for a single company, only those marked as active will be retained.

2.3 LEI Data Enrichment  
   • As a user, I want each active company record to be enriched with its Legal Entity Identifier (LEI) if available.  
   • As a user, I expect that if no LEI data exists for a company, the field will be marked as “Not Available.”

2.4 Output  
   • As a user, I want the final result to be provided in a structured JSON (or potentially CSV) format with the following details:  
       - Company Name  
       - Business ID  
       - Company Type  
       - Registration Date  
       - Status (Active/Inactive)  
       - LEI (or “Not Available”)
   • As a user, I want the application to support pagination when the number of results exceeds a single page.

─────────────────────────────  
3. API Endpoints  
(Endpoints follow RESTful best practices, using nouns only)

3.1 GET /companies  
   • Description: Retrieves company details based on search parameters.  
   • Request Parameters (Query Parameters):  
     - name (string, required): The company name or partial name.  
     - location (string, optional): Town or city.  
     - businessId (string, optional): Business ID.  
     - companyForm (string, optional): Type of company, from a predefined enum list.  
     - page (integer, optional): Page number (if results span multiple pages).  
   • Response:  
     - 200 OK  
       {  
         "companies": [  
           {  
             "companyName": "Example Company",  
             "businessId": "1234567-8",  
             "companyType": "OY",  
             "registrationDate": "YYYY-MM-DD",  
             "status": "Active",  
             "lei": "LEI-EXAMPLE"  
           }  
         ]  
       }  
     - 400 Bad Request  
       { "error": "Invalid parameters" }

3.2 GET /companies/{id}/lei  
   • Description: Retrieves the LEI for a specific company using its unique identifier.  
   • Request Parameter (Path Parameter):  
     - id (string, required): The unique company identifier.  
   • Response:  
     - 200 OK  
       { "lei": "LEI-EXAMPLE" }  
     - 404 Not Found  
       { "error": "Company not found" }

─────────────────────────────  
4. Visual Representations

4.1 User Journey Diagram (Mermaid Syntax)
-------------------------------------------
journey
    title User Journey for Company Data Retrieval
    section Search for Company
      User enters company name: 5: User
      Application queries API: 4: Application
      Application retrieves data: 5: Application
    section Filter Results
      Application filters inactive companies: 5: Application
      User receives a list of active companies: 5: User
    section Enrich Data
      Application fetches LEI for each active company: 4: Application
      User receives enriched data: 5: User
-------------------------------------------

4.2 Sequence Diagram (Mermaid Syntax)
-------------------------------------------
sequenceDiagram
    participant User
    participant Application
    participant API

    User->>Application: Search for company by name
    Application->>API: GET /companies?name=value[&other=parameters]
    API-->>Application: Return company data
    Application->>Application: Filter inactive companies
    Application->>User: Display list of active companies
    User->>Application: Request LEI for a selected company
    Application->>API: GET /companies/{id}/lei
    API-->>Application: Return LEI data
    Application->>User: Display company details with LEI
-------------------------------------------

─────────────────────────────  
5. Additional Considerations  
   • Error handling and logging should be implemented, especially for API rate limiting and LEI retrieval failures.  
   • Consider performance requirements, such as response time and handling large datasets via pagination.  
   • Evaluate potential extensions such as supporting CSV output format based on user preference.

This comprehensive document captures the core functional requirements, API specifications, and user interactions to support the next steps toward formalizing the specification and building the backend application.