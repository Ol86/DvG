# Camunda

This package holds the Camunda BPMN engine and related tools. It is used by the `camunda` package to provide BPMN workflow capabilities.
The main components of this package include:
- `Job-Workers`: These are responsible for executing tasks defined in BPMN workflows.
  - `RegisterInvoiceWorker`: A worker that handles invoice processing tasks.
  - `ExecutePaymentWorker`: A worker that handles payment execution tasks.
