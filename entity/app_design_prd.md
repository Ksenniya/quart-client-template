# Product Requirements Document (PRD) for Cyoda Design

## Introduction

This document outlines the Cyoda design for managing the download, analysis, reporting, and monitoring of London Houses Data. The design is aligned with the specified requirements and explains the structure of entities, their workflows, and an event-driven architecture. The document includes mermaid diagrams to visualize workflows and relationships between entities, emphasizing the orchestration of the flow through a JOB entity and the addition of a monitoring entity.

## What is Cyoda?

Cyoda is a serverless, event-driven framework that helps manage workflows through entities that represent jobs and data. Each entity has defined states, and transitions between these states are governed by events, enabling efficient and scalable processing.

## Cyoda Design JSON Overview

The Cyoda design JSON outlines the following entities and their properties:

1. **Data Collection Job (`data_collection_job`)**:
   - **Type**: JOB
   - **Source**: SCHEDULED
   - **Description**: This job orchestrates the entire process, responsible for downloading the London Houses Data, analyzing it, generating a report, and monitoring the overall workflow.

2. **Raw Data Entity (`london_houses_raw_data`)**:
   - **Type**: EXTERNAL_SOURCES_PULL_BASED_RAW_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Stores the raw data downloaded by the data collection job.

3. **Analysis Result Entity (`london_houses_analysis_result`)**:
   - **Type**: SECONDARY_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Holds the results of the data analysis performed on the raw data.

4. **Report Entity (`london_houses_report`)**:
   - **Type**: SECONDARY_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Contains the generated report based on the analysis results.

5. **Monitoring Entity (`workflow_monitor`)**:
   - **Type**: UTIL
   - **Source**: ENTITY_EVENT
   - **Description**: Monitors the status of the data collection job and alerts if any issues arise during the workflow.

### Entity Workflow Diagrams

#### Flowchart for Data Collection Workflow

```mermaid
flowchart TD
    A[Start State] -->|trigger: download_london_houses_data| B[data_downloaded]
    B -->|trigger: analyze_london_houses_data| C[data_analyzed]
    C -->|trigger: generate_report| D[report_generated]
    D -->|trigger: monitor_workflow| E[workflow_monitored]
    E -->|End of Job| F[Job Completed]

    class A,B,C,D,E,F automated;
```

#### Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Scheduler
    participant Data Collection Job
    participant Raw Data Entity
    participant Analysis Result Entity
    participant Report Entity
    participant Workflow Monitor
    
    User->>Scheduler: Schedule data collection job
    Scheduler->>Data Collection Job: Trigger data collection
    Data Collection Job->>Raw Data Entity: Download London Houses Data
    Raw Data Entity-->>Data Collection Job: Data downloaded
    Data Collection Job->>Analysis Result Entity: Analyze data
    Analysis Result Entity-->>Data Collection Job: Analysis complete
    Data Collection Job->>Report Entity: Generate report
    Report Entity-->>Data Collection Job: Report generated
    Data Collection Job->>Workflow Monitor: Monitor job status
    Workflow Monitor-->>Data Collection Job: Status monitored
    Data Collection Job->>User: Send report
```

### Entity Relationships Diagram

```mermaid
graph TD;
    A[data_collection_job] -->|triggers| B[london_houses_raw_data];
    B -->|analyzes into| C[london_houses_analysis_result];
    C -->|generates| D[london_houses_report];
    A -->|monitors| E[workflow_monitor];
```

### User Journey

```mermaid
journey
    title User Flow for Downloading, Analyzing, and Monitoring London Houses Data
    section Start
      User initiates the process: 5: User
      User schedules the data collection job: 5: User
    section Data Collection
      Scheduler triggers the data collection job: 5: Scheduler
      Data collection job downloads data: 5: Data Collection Job
    section Analysis
      Data collection job analyzes data: 4: Data Collection Job
    section Reporting
      Data collection job generates report: 5: Data Collection Job
      User receives the report: 5: User
    section Monitoring
      Workflow monitor checks job status: 5: Workflow Monitor
      User receives monitoring updates: 5: User
```

## Conclusion

The Cyoda design effectively aligns with the requirements for orchestrating the download, analysis, reporting, and monitoring of London Houses Data through a JOB entity. By utilizing an event-driven model, the application efficiently manages state transitions among entities, ensuring a smooth and automated process from data collection to report delivery and monitoring.

This PRD serves as a foundation for implementation, guiding the technical team through the specifics of the Cyoda architecture while providing clarity for users new to the framework.