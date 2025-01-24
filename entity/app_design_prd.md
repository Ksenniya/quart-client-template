# Product Requirements Document (PRD) for Cyoda Design

## Introduction

This document delineates the Cyoda-based application designed to manage the download, analysis, and reporting of London Houses Data. It elucidates how the Cyoda design aligns with the stated requirements, providing insights into the structure of entities, workflows, and the event-driven architecture that supports the application. The design is represented in a human-readable format, supplemented by various markdown diagrams for clarity.

## What is Cyoda?

Cyoda is a serverless, event-driven framework facilitating the management of workflows through entities that represent jobs and data. Each entity has a defined state, and transitions between states are governed by events occurring within the system—enabling responsive and scalable architecture.

## Cyoda Entity Database

The Cyoda design JSON outlines several entities for our application, complete with their workflows and transitions:

1. **Data Ingestion Job (`data_ingestion_job`)**:
   - **Type**: JOB
   - **Source**: SCHEDULED
   - **Description**: Manages the process of downloading the raw data.

2. **Raw Data Entity (`raw_data_entity`)**:
   - **Type**: EXTERNAL_SOURCES_PULL_BASED_RAW_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Stores the raw data that has been downloaded.

3. **Analysis Report Entity (`analysis_report_entity`)**:
   - **Type**: SECONDARY_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Contains the results of the data analysis.

4. **Report Entity (`report_entity`)**:
   - **Type**: SECONDARY_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Holds the generated report based on the analysis.

## Workflow Overview

The workflows in Cyoda define how each job entity operates through a series of transitions:

- **Data Ingestion**: Initiates the downloading of raw data.
- **Data Analysis**: Analyzes the ingested raw data using Pandas.
- **Report Generation**: Generates and saves a report based on the analysis.

### Flowchart for Data Ingestion Job Workflow

```mermaid
flowchart TD
    A[Start State] -->|transition: scheduled_ingestion, processor: ingest_raw_data, processor attributes: sync_process=true| B[Data Ingested]
    B -->|transition: analyze_data, processor: analyze_raw_data, processor attributes: sync_process=true| C[Data Analyzed]
    C -->|transition: generate_report, processor: generate_report, processor attributes: sync_process=true| D[Report Generated]

    %% Decision point for criteria
    B -->|criteria: Check if data is available| D1{Decision: Check Data Availability}
    D1 -->|true| C
    D1 -->|false| E[Error: Data not available]

    class A,B,C,D,D1 automated;
```

### Entity Diagram

```mermaid
graph TD;
    A[data_ingestion_job] -->|triggers| B[raw_data_entity];
    B -->|analyzes into| C[analysis_report_entity];
    C -->|generates| D[report_entity];
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Scheduler
    participant Data Ingestion Job
    participant Raw Data Entity
    participant Analysis Report Entity
    participant Report Entity

    User->>Scheduler: Schedule data ingestion job
    Scheduler->>Data Ingestion Job: Trigger scheduled ingestion
    Data Ingestion Job->>Raw Data Entity: Ingest data
    Raw Data Entity-->>Data Ingestion Job: Data ingested
    Data Ingestion Job->>Analysis Report Entity: Analyze data
    Analysis Report Entity-->>Data Ingestion Job: Data analyzed
    Data Ingestion Job->>Report Entity: Generate report
    Report Entity-->>Data Ingestion Job: Report generated
```

## Conclusion

The Cyoda design effectively aligns with the requirements for creating a robust data ingestion and reporting application. By utilizing an event-driven model, the application efficiently manages state transitions of each entity involved, from data ingestion through to report generation. The outlined entities, workflows, and events comprehensively address the application needs, ensuring a smooth and automated process.

The provided diagrams visualize workflows and entity relationships, promoting understanding and facilitating easier implementation by the technical team. This PRD serves as a foundation for development, guiding the team through the specifics of the Cyoda architecture while clarifying usage for new users.