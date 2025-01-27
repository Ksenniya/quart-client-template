# Product Requirements Document (PRD) for Cyoda Design

## Introduction

This document explains the Cyoda-based application designed to download, analyze, and report on London Houses Data. The design outlines the necessary entities, workflows, and how they align with the specified requirements. It provides a comprehensive overview of the Cyoda framework through the Cyoda design JSON.

## Overview of Cyoda Design JSON

The Cyoda design JSON comprises several entities primarily focused on data ingestion, processing, and report generation. Each entity has defined workflows that dictate its behavior through state transitions. The design incorporates a well-structured approach, ensuring that each process is automated and can react to events.

### Cyoda Entities

1. **Data Ingestion Job (`data_ingestion_job`)**:
   - **Type**: JOB
   - **Source**: SCHEDULED
   - **Workflow**: Responsible for downloading, analyzing, and generating a report from the data.
   - **Transitions**:
     - `scheduled_ingestion`: Initiates the data ingestion from an API.
     - `analyze_data`: Analyzes the ingested data using pandas.
     - `generate_report`: Creates a report from the analyzed data.

2. **Raw Data Entity (`raw_data_entity`)**:
   - **Type**: EXTERNAL_SOURCES_PULL_BASED_RAW_DATA
   - **Source**: ENTITY_EVENT
   - **Workflow**: Represents the raw data obtained from external sources.

3. **Analyzed Data Entity (`analyzed_data_entity`)**:
   - **Type**: SECONDARY_DATA
   - **Source**: ENTITY_EVENT
   - **Workflow**: Represents the analyzed data after data processing.

4. **Report Entity (`report_entity`)**:
   - **Type**: SECONDARY_DATA
   - **Source**: ENTITY_EVENT
   - **Workflow**: Contains the generated report after analyzing the data.

5. **Monitoring Entity (`monitoring_entity`)**:
   - **Type**: SECONDARY_DATA
   - **Source**: ENTITY_EVENT
   - **Workflow**: Tracks the status and performance of the data processing workflows.

## Workflows as Flowcharts

### Data Ingestion Job Workflow
```mermaid
flowchart TD
    A[Start State] -->|transition: scheduled_ingestion, processor: ingest_raw_data| B[Data Ingested]
    B -->|transition: analyze_data, processor: analyze_data_with_pandas| C[Data Analyzed]
    C -->|transition: generate_report, processor: generate_report| D[Report Generated]

    class A,B,C,D automated;
```

### Entity Relationship Diagram
```mermaid
graph TD;
    A[data_ingestion_job] -->|triggers| B[raw_data_entity];
    B -->|transforms into| C[analyzed_data_entity];
    C -->|generates| D[report_entity];
    A -->|monitored by| E[monitoring_entity];
```

### Sequence Diagram
```mermaid
sequenceDiagram
    participant User
    participant Scheduler
    participant Data Ingestion Job
    participant Raw Data Entity
    participant Analyzed Data Entity
    participant Report Entity
    participant Monitoring Entity

    User->>Scheduler: Schedule data ingestion job
    Scheduler->>Data Ingestion Job: Trigger scheduled_ingestion
    Data Ingestion Job->>Raw Data Entity: Ingest data
    Raw Data Entity-->>Data Ingestion Job: Data ingested
    Data Ingestion Job->>Analyzed Data Entity: Analyze data
    Analyzed Data Entity-->>Data Ingestion Job: Data analyzed
    Data Ingestion Job->>Report Entity: Generate report
    Report Entity-->>Data Ingestion Job: Report generated
    Data Ingestion Job->>Monitoring Entity: Log job performance and status
```

### User Journey Diagram
```mermaid
journey
    title User Flow for Downloading and Analyzing London Houses Data
    section Start
      User initiates the process: 5: User
      User schedules the data ingestion job: 5: User
    section Ingestion
      Data ingestion job triggers: 5: System
      Raw data is stored: 4: System
    section Analysis
      Data is analyzed using pandas: 5: System
    section Reporting
      Report is generated: 5: System
      User receives report: 5: User
    section Monitoring
      Job performance is logged: 5: System
      Monitoring entity reports status: 5: System
```

## Conclusion

The Cyoda design outlined in this document effectively meets the requirements for downloading, analyzing, and reporting on London Houses Data. By leveraging an event-driven architecture, each entity can operate autonomously based on state transitions triggered by specific events. The provided workflows, flowcharts, and diagrams enhance clarity and provide a comprehensive understanding of the Cyoda framework and its alignment with the application's objectives.