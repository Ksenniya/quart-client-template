Sure! Here's a complete Product Requirements Document (PRD) based on everything we've discussed, including your requirements, workflows, entities, and diagrams. 

---

# Product Requirements Document (PRD) for London Houses Data Analysis Application

## Introduction

This document outlines the requirements for the London Houses Data Analysis application. The application will enable users to upload property data, analyze it, and generate reports. It provides a comprehensive overview of the application architecture, user stories, workflows, entities, and diagrams.

## User Requirements

### User Stories

1. **As a user**, I want to upload a CSV file with property data so that I can analyze it easily.
2. **As a user**, I want to visualize the analysis results through charts and graphs, helping me understand property trends better.
3. **As a user**, I want to generate a report from the analyzed data so that I can share insights with others.
4. **As a user**, I want to save my reports for future reference, so I don’t have to redo the analysis.

### User Journey Diagram

```mermaid
journey
    title User Journey for Analyzing London Houses Data
    section Upload Data
      User uploads CSV file: 5: User
    section Analyze Data
      System processes data: 4: System
      System performs analysis: 4: System
    section Visualize Results
      System generates charts: 5: System
      User views visualizations: 5: User
    section Generate Report
      User clicks "Generate Report": 5: User
      System creates report: 4: System
    section Save Report
      User saves report: 5: User
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant System
    participant ReportGenerator

    User->>System: Upload CSV file
    System->>System: Process file
    System->>System: Analyze data
    System->>User: Display visualizations
    User->>ReportGenerator: Request report
    ReportGenerator->>System: Generate report from analysis
    System->>User: Provide downloaded report
```

## Entity Outline

### 1. Data Ingestion Job
- **Entity Type**: JOB
- **Source**: SCHEDULED
- **Description**: Responsible for triggering the data ingestion process from the CSV file.

### 2. Raw Data Entity
- **Entity Type**: EXTERNAL_SOURCES_PULL_BASED_RAW_DATA
- **Source**: ENTITY_EVENT
- **Description**: Stores the raw property data extracted from the uploaded CSV file.

### 3. Analyzed Data Entity
- **Entity Type**: SECONDARY_DATA
- **Source**: ENTITY_EVENT
- **Description**: Contains the analyzed data after applying pandas to the raw data.

### 4. Report Entity
- **Entity Type**: SECONDARY_DATA
- **Source**: ENTITY_EVENT
- **Description**: Holds the generated report based on the analyzed data.

### Entities Diagram

```mermaid
graph TD;
    A[Data Ingestion Job] --> B[Raw Data Entity];
    B --> C[Analyzed Data Entity];
    C --> D[Report Entity];
```

## Proposed Workflow: Data Ingestion Job Workflow

**Description**: This workflow manages the entire process of data ingestion, starting from the scheduled job to the creation of raw data entities.

**How It’s Launched**: The workflow is triggered based on a scheduled time set for the Data Ingestion Job. When the scheduled time arrives, the workflow starts processing the uploaded CSV file.

**Flowchart**:

```mermaid
flowchart TD
   A[Start State] -->|transition: start_data_ingestion, processor: ingest_raw_data, processor attributes: sync_process=true, new_transaction_for_async=false, none_transactional_for_async=false| B[Data Ingestion Successful]
   B -->|transition: process_raw_data, processor: process_raw_data, processor attributes: sync_process=true| C[Raw Data Created]
   C --> D[End State]

   %% Decision point for success
   B -->|criteria: success, data exists| D1{Decision: Check for Data}
   D1 -->|true| C
   D1 -->|false| E[Error: No Data Found]

   class A,B,C,D,D1 automated;
```

## Conclusion

The London Houses Data Analysis application is designed to provide a user-friendly platform for uploading, analyzing, and reporting on property data. The outlined user stories, workflows, and entities create a robust foundation for development while ensuring that user needs are met efficiently.

---

Feel free to make any adjustments or let me know if you need additional details! 😊