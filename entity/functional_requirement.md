# Functional Requirements for Bitcoin Conversion Report Application

## Overview

The application provides a RESTful API for generating and retrieving Bitcoin conversion reports. It fetches current Bitcoin-to-USD and Bitcoin-to-EUR conversion rates, stores the results, and sends email reports.

## API Endpoints

### 1. POST /job

#### Description
- Initiates the report creation process.
- Fetches the latest Bitcoin conversion rates from an external service.
- Stores the report with relevant data (conversion rates, timestamp, report ID).
- Sends an email with the report details.

#### Request Format
- **Method**: POST  
- **URL**: `/job`  
- **Headers**: `Content-Type: application/json`  
- **Body**: (No payload required)

Example:
```json
{}
```

#### Response Format
- **Status**: 200 OK  
- **Body**:
```json
{
  "report_id": "unique_report_identifier",
  "status": "Report generated and email sent successfully",
  "rates": {
    "BTC_USD": "value_in_usd",
    "BTC_EUR": "value_in_eur"
  },
  "timestamp": "ISO8601_timestamp"
}
```

### 2. GET /report/{id}

#### Description
- Retrieves a specific report by its ID.
- Returns the conversion rate information and report metadata.

#### Request Format
- **Method**: GET  
- **URL**: `/report/{id}`  
- **Headers**: `Accept: application/json`  
- **Path Parameter**: `id` – Unique report identifier

#### Response Format
- **Status**: 200 OK  
- **Body**:
```json
{
  "report_id": "unique_report_identifier",
  "rates": {
    "BTC_USD": "value_in_usd",
    "BTC_EUR": "value_in_eur"
  },
  "timestamp": "ISO8601_timestamp",
  "email_status": "sent"
}
```

If the report is not found:
```json
{
  "error": "Report not found"
}
```

### 3. GET /reports

#### Description
- Retrieves all stored reports. Supports pagination if there are many reports.

#### Request Format
- **Method**: GET  
- **URL**: `/reports`  
- **Headers**: `Accept: application/json`  
- **Optional Query Parameters**:
  - `page`: Page number
  - `size`: Number of reports per page

#### Response Format
- **Status**: 200 OK  
- **Body**:
```json
{
  "reports": [
    {
      "report_id": "unique_report_identifier",
      "rates": {
        "BTC_USD": "value_in_usd",
        "BTC_EUR": "value_in_eur"
      },
      "timestamp": "ISO8601_timestamp"
    }
    // ... additional reports
  ],
  "page": 1,
  "size": 10,
  "total_reports": 100
}
```

## User-App Interaction Diagrams

### Sequence Diagram for Report Generation and Retrieval

```mermaid
sequenceDiagram
    participant User
    participant API
    participant ExternalAPI as "BTC Data Service"
    participant EmailService
    participant Database

    User->>API: POST /job
    API->>ExternalAPI: Fetch BTC/USD and BTC/EUR rates
    ExternalAPI-->>API: Return conversion rates
    API->>Database: Store report (rates, timestamp, report_id)
    API->>EmailService: Send email with report details
    EmailService-->>API: Email sent confirmation
    API-->>User: Respond with report_id, rates, timestamp

    User->>API: GET /report/{id}
    API->>Database: Retrieve report by id
    Database-->>API: Return report data
    API-->>User: Send report data

    User->>API: GET /reports
    API->>Database: Retrieve all reports (with pagination if applicable)
    Database-->>API: Return list of reports
    API-->>User: Return reports list
```

### User Journey Diagram

```mermaid
journey
    title User Journey for Generating and Retrieving Reports
    section Report Generation
      Initiate Report Creation: 5: User, API
      Fetch Conversion Rates: 4: API, ExternalBTCSource
      Store Report Data: 4: API, Database
      Trigger Email Notification: 3: API, EmailService
    section Report Retrieval
      Retrieve Specific Report: 5: User, API, Database
      List All Reports: 4: User, API, Database
```