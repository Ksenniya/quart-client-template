# Product Requirements Document (PRD) for Cyoda Design

## Introduction

This document outlines the Cyoda-based application designed to manage the ingestion, analysis, and reporting of London Houses Data. It explains how the provided Cyoda design JSON structure aligns with the specified requirement, delineating entities, workflows, and their relationships. The document also includes various markdown diagrams to illustrate the workflows, entity relationships, and processes within the system.

## Cyoda Design Overview

In the Cyoda architecture, workflows are structured around "entities" which represent different components of the data processing lifecycle. Each entity has defined states and transitions that dictate how it behaves in response to events.

### Entities and Workflows

The following entities are defined in the Cyoda design JSON:

1. **Data Ingestion Job (`data_ingestion_job`)**
   - Type: JOB
   - Source: SCHEDULED
   - Description: Responsible for ingesting data from specified sources.

2. **Raw Data Entity (`raw_data_entity`)**
   - Type: EXTERNAL_SOURCES_PULL_BASED_RAW_DATA
   - Source: ENTITY_EVENT
   - Description: Stores the raw data that has been ingested.

3. **Analyzed Data Entity (`analyzed_data_entity`)**
   - Type: SECONDARY_DATA
   - Source: ENTITY_EVENT
   - Description: Contains data that has been analyzed using pandas.

4. **Report Entity (`report_entity`)**
   - Type: SECONDARY_DATA
   - Source: ENTITY_EVENT
   - Description: Contains the generated report derived from the analyzed data.

## Workflow Flowcharts

### Data Ingestion Job Workflow

```mermaid
flowchart TD
    A[Start State] -->|transition: scheduled_ingestion, processor: ingest_raw_data, processor attributes: sync_process=false| B[data_ingested]
    B --> C[End State]

    class A,B,C automated;
```

### Analyzed Data Workflow

```mermaid
flowchart TD
    A[data_ingested] -->|transition: analyze_raw_data, processor: analyze_data, processor attributes: sync_process=false| B[data_analyzed]
    B --> C[End State]

    class A,B,C automated;
```

### Report Generation Workflow

```mermaid
flowchart TD
    A[data_analyzed] -->|transition: generate_report, processor: generate_report_process, processor attributes: sync_process=false| B[report_generated]
    B --> C[End State]

    class A,B,C automated;
```

## Entity Relationships and State Transitions

```mermaid
graph TD;
    A[data_ingestion_job] -->|triggers| B[raw_data_entity];
    B -->|analyzes into| C[analyzed_data_entity];
    C -->|generates| D[report_entity];
```

## Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Scheduler
    participant Data Ingestion Job
    participant Raw Data Entity
    participant Analyzed Data Entity
    participant Report Entity

    User->>Scheduler: Schedule data ingestion job
    Scheduler->>Data Ingestion Job: Trigger scheduled ingestion
    Data Ingestion Job->>Raw Data Entity: Ingest data
    Raw Data Entity-->>Data Ingestion Job: Data ingested
    Data Ingestion Job->>Analyzed Data Entity: Analyze data
    Analyzed Data Entity-->>Data Ingestion Job: Data analyzed
    Data Ingestion Job->>Report Entity: Generate report
    Report Entity-->>Data Ingestion Job: Report generated
```

## Conclusion

The Cyoda design efficiently encapsulates the requirements for processing London Houses Data, from ingestion to report generation. By leveraging an event-driven architecture with defined entities and workflows, the application ensures smooth data processing and reporting. The structures outlined in this document provide a comprehensive overview for developers and stakeholders, ensuring clarity and alignment with the project goals.